import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Alert, Budget, Category, Goal, Transaction
from .forms import CategoryForm


def get_month_start(date):
    return date.replace(day=1)


def ensure_default_categories(user):
    defaults = [
        {'name': 'Moradia', 'icon': '🏠'},
        {'name': 'Alimentação', 'icon': '🍔'},
        {'name': 'Lazer', 'icon': '🎮'},
        {'name': 'Educação', 'icon': '📚'},
        {'name': 'Transporte', 'icon': '🚌'},
        {'name': 'Poupança', 'icon': '💰'},
        {'name': 'Outros', 'icon': '🔧'},
    ]

    categories = []
    for item in defaults:
        category, _ = Category.objects.get_or_create(
            user=user,
            name=item['name'],
            defaults={'icon': item['icon']},
        )
        categories.append(category)
    return Category.objects.filter(user=user).order_by('name')


def refresh_alerts(user):
    today = timezone.localdate()
    current_month = get_month_start(today)

    income = Transaction.objects.filter(user=user, type='income').aggregate(total=Sum('amount'))['total'] or 0
    expense = Transaction.objects.filter(user=user, type='expense').aggregate(total=Sum('amount'))['total'] or 0
    balance = income - expense

    if balance < 0:
        Alert.objects.update_or_create(
            user=user,
            alert_type='saldo_negativo',
            category=None,
            goal=None,
            defaults={
                'title': 'Saldo negativo',
                'message': 'Seu saldo atual está negativo. Reveja seus lançamentos e reduza gastos.',
                'read': False,
            }
        )

    budgets = Budget.objects.filter(user=user, month=current_month).select_related('category')
    for budget in budgets:
        spent = Transaction.objects.filter(
            user=user,
            category=budget.category,
            type='expense',
            date__year=current_month.year,
            date__month=current_month.month,
        ).aggregate(total=Sum('amount'))['total'] or 0

        if budget.amount > 0:
            if spent >= budget.amount:
                Alert.objects.update_or_create(
                    user=user,
                    alert_type='orcamento_100',
                    category=budget.category,
                    goal=None,
                    defaults={
                        'title': f'Orçamento {budget.category.name} estourado',
                        'message': f'Você gastou R$ {spent:.2f} de R$ {budget.amount:.2f} em {budget.category.name}.',
                        'read': False,
                    }
                )
            elif spent >= budget.amount * Decimal('0.8'):
                Alert.objects.update_or_create(
                    user=user,
                    alert_type='orcamento_80',
                    category=budget.category,
                    goal=None,
                    defaults={
                        'title': f'Orçamento {budget.category.name} em alerta',
                        'message': f'Você usou {spent:.2f} de {budget.amount:.2f} em {budget.category.name}.',
                        'read': False,
                    }
                )

    goals = Goal.objects.filter(user=user, deadline__isnull=False)
    for goal in goals:
        if goal.current_amount < goal.target_amount:
            days_left = (goal.deadline - today).days
            if 0 <= days_left <= 30:
                Alert.objects.update_or_create(
                    user=user,
                    alert_type='meta_prazo',
                    category=None,
                    goal=goal,
                    defaults={
                        'title': f'Meta {goal.name} com prazo próximo',
                        'message': f'A meta "{goal.name}" vence em {goal.deadline.strftime("%d/%m/%Y")}. Faltam R$ {goal.target_amount - goal.current_amount:.2f}.',
                        'read': False,
                    }
                )


class IndexView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def get(self, request, *args, **kwargs):
        user = request.user
        now = timezone.localdate()
        current_month = get_month_start(now)

        ensure_default_categories(user)

        income_total = Transaction.objects.filter(user=user, type='income').aggregate(total=Sum('amount'))['total'] or 0
        expense_total = Transaction.objects.filter(user=user, type='expense').aggregate(total=Sum('amount'))['total'] or 0
        current_balance = income_total - expense_total

        monthly_income = Transaction.objects.filter(
            user=user,
            type='income',
            date__year=current_month.year,
            date__month=current_month.month,
        ).aggregate(total=Sum('amount'))['total'] or 0

        monthly_expenses = Transaction.objects.filter(
            user=user,
            type='expense',
            date__year=current_month.year,
            date__month=current_month.month,
        ).aggregate(total=Sum('amount'))['total'] or 0

        budgets = Budget.objects.filter(user=user, month=current_month).select_related('category')
        budget_usage = []
        total_percent = 0
        for budget in budgets:
            spent = Transaction.objects.filter(
                user=user,
                category=budget.category,
                type='expense',
                date__year=current_month.year,
                date__month=current_month.month,
            ).aggregate(total=Sum('amount'))['total'] or 0
            percent = float((spent / budget.amount) * 100) if budget.amount > 0 else 0
            budget_usage.append({
                'category': budget.category.name,
                'icon': budget.category.icon,
                'spent': spent,
                'budget': budget.amount,
                'percent': percent,
                'label_class': 'green' if percent < 50 else 'yellow' if percent < 80 else 'red',
            })
            total_percent += percent

        if budgets.exists():
            total_percent = total_percent / budgets.count()

        recent_transactions = Transaction.objects.filter(user=user).select_related('category').order_by('-date')[:5]

        month_labels = []
        income_data = []
        expense_data = []
        for offset in range(5, -1, -1):
            month = current_month - timedelta(days=30 * offset)
            month = month.replace(day=1)
            month_labels.append(month.strftime('%b/%y'))
            income_data.append(float(Transaction.objects.filter(
                user=user,
                type='income',
                date__year=month.year,
                date__month=month.month,
            ).aggregate(total=Sum('amount'))['total'] or 0))
            expense_data.append(float(Transaction.objects.filter(
                user=user,
                type='expense',
                date__year=month.year,
                date__month=month.month,
            ).aggregate(total=Sum('amount'))['total'] or 0))

        category_expenses = Transaction.objects.filter(
            user=user,
            type='expense',
            date__year=current_month.year,
            date__month=current_month.month,
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')

        doughnut_labels = [item['category__name'] for item in category_expenses]
        doughnut_data = [float(item['total']) for item in category_expenses]

        context = {
            'current_balance': current_balance,
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'budget_used_percent': total_percent,
            'recent_transactions': recent_transactions,
            'budget_usage': budget_usage,
            'categories': Category.objects.filter(user=user).order_by('name'),
            'bar_chart_labels': json.dumps(month_labels),
            'bar_chart_income': json.dumps(income_data),
            'bar_chart_expenses': json.dumps(expense_data),
            'doughnut_labels': json.dumps(doughnut_labels),
            'doughnut_data': json.dumps(doughnut_data),
        }
        return render(request, 'pages/dashboard.html', context)


class LancamentosView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def get(self, request, *args, **kwargs):
        user = request.user
        ensure_default_categories(user)

        all_transactions = Transaction.objects.filter(user=user).select_related('category').order_by('-date')
        income_transactions = all_transactions.filter(type='income')
        expense_transactions = all_transactions.filter(type='expense')
        month_dates = all_transactions.dates('date', 'month', order='DESC')[:6]
        months = [month.strftime('%b/%y') for month in month_dates]
        if not months:
            months = [timezone.localdate().strftime('%b/%y')]

        context = {
            'categories': Category.objects.filter(user=user).order_by('name'),
            'income_transactions': income_transactions,
            'expense_transactions': expense_transactions,
            'months': months,
        }
        return render(request, 'pages/lancamentos.html', context)


class OrcamentoView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def get(self, request, *args, **kwargs):
        user = request.user
        ensure_default_categories(user)

        today = timezone.localdate()
        current_month = get_month_start(today)
        budgets = Budget.objects.filter(user=user, month=current_month).select_related('category')
        categories = Category.objects.filter(user=user).order_by('name')

        budget_items = []
        total_budget = Decimal('0')
        total_spent = Decimal('0')
        orc_labels = []
        orc_values = []
        for category in categories:
            budget = budgets.filter(category=category).first()
            amount = budget.amount if budget else Decimal('0')
            spent = Transaction.objects.filter(
                user=user,
                category=category,
                type='expense',
                date__year=current_month.year,
                date__month=current_month.month,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            percent = float((spent / amount) * 100) if amount > 0 else 0
            budget_items.append({
                'category': category,
                'amount': amount,
                'spent': spent,
                'percent': percent,
                'status': 'green' if percent < 50 else 'yellow' if percent < 80 else 'red',
            })
            if amount > 0:
                total_budget += amount
                total_spent += spent
                orc_labels.append(category.icon or category.name)
                orc_values.append(float(amount))

        total_available = total_budget - total_spent
        used_percent = float((total_spent / total_budget) * 100) if total_budget > 0 else 0

        context = {
            'categories': categories,
            'budget_items': budget_items,
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_available': total_available,
            'budget_used_percent': used_percent,
            'orcamento_labels': json.dumps(orc_labels),
            'orcamento_values': json.dumps(orc_values),
        }
        print("Context sendo enviado:", context)
        return render(request, 'pages/orcamento.html', context)

    def post(self, request, *args, **kwargs):
        user = request.user
        today = timezone.localdate()
        current_month = get_month_start(today)
        categories = Category.objects.filter(user=user)

        for category in categories:
            field_name = f'budget_{category.id}'
            amount = request.POST.get(field_name, '').strip()
            if amount:
                try:
                    parsed_amount = Decimal(amount)
                except InvalidOperation:
                    continue
                Budget.objects.update_or_create(
                    user=user,
                    category=category,
                    month=current_month,
                    defaults={'amount': parsed_amount},
                )
            else:
                Budget.objects.filter(user=user, category=category, month=current_month).delete()

        return redirect('orcamento')


class AddCategoryView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, *args, **kwargs):
        print("=== AddCategoryView chamada ===")
        print("Método:", request.method)
        print("POST data:", dict(request.POST))
        print("User:", request.user)
        print("User is authenticated:", request.user.is_authenticated)
        
        user = request.user
        form = CategoryForm(request.POST)
        
        print("Form is valid:", form.is_valid())
        if not form.is_valid():
            print("Form errors:", dict(form.errors))
            print("Form non_field_errors:", form.non_field_errors())
        
        if form.is_valid():
            category = form.save(commit=False)
            category.user = user
            category.save()
            print("Categoria salva:", category.name, category.icon)
            return JsonResponse({
                'success': True,
                'category_id': category.id,
                'category_name': category.name,
                'category_icon': category.icon,
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            }, status=400)


class EditCategoryView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, *args, **kwargs):
        print("=== EditCategoryView chamada ===")
        user = request.user
        category_id = request.POST.get('category_id')
        
        try:
            category = Category.objects.get(id=category_id, user=user)
        except Category.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Categoria não encontrada'
            }, status=404)
        
        form = CategoryForm(request.POST, instance=category)
        
        if form.is_valid():
            category = form.save()
            print("Categoria atualizada:", category.name, category.icon)
            return JsonResponse({
                'success': True,
                'category_id': category.id,
                'category_name': category.name,
                'category_icon': category.icon,
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            }, status=400)


class DeleteCategoryView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, *args, **kwargs):
        print("=== DeleteCategoryView chamada ===")
        user = request.user
        category_id = request.POST.get('category_id')
        
        try:
            category = Category.objects.get(id=category_id, user=user)
        except Category.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Categoria não encontrada'
            }, status=404)
        
        # Verificar se a categoria tem transações associadas
        has_transactions = Transaction.objects.filter(user=user, category=category).exists()
        has_budget = Budget.objects.filter(user=user, category=category).exists()
        
        if has_transactions or has_budget:
            return JsonResponse({
                'success': False,
                'error': 'Não é possível excluir esta categoria pois ela possui lançamentos ou orçamentos associados. Transfira os dados para outra categoria primeiro.'
            }, status=400)
        
        category_name = category.name
        category.delete()
        
        print("Categoria excluída:", category_name)
        return JsonResponse({
            'success': True,
            'message': f'Categoria "{category_name}" excluída com sucesso'
        })


class RelatoriosView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def get(self, request, *args, **kwargs):
        user = request.user
        ensure_default_categories(user)

        today = timezone.localdate()
        current_month = get_month_start(today)

        category_expenses = Transaction.objects.filter(
            user=user,
            type='expense',
            date__year=current_month.year,
            date__month=current_month.month,
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')

        months = []
        incomes = []
        expenses = []
        balances = []
        for offset in range(5, -1, -1):
            month = current_month - timedelta(days=30 * offset)
            month = month.replace(day=1)
            months.append(month.strftime('%b/%y'))
            inc = Transaction.objects.filter(
                user=user,
                type='income',
                date__year=month.year,
                date__month=month.month,
            ).aggregate(total=Sum('amount'))['total'] or 0
            exp = Transaction.objects.filter(
                user=user,
                type='expense',
                date__year=month.year,
                date__month=month.month,
            ).aggregate(total=Sum('amount'))['total'] or 0
            incomes.append(float(inc))
            expenses.append(float(exp))
            balances.append(float(inc - exp))

        semestral = []
        for offset in range(5, -1, -1):
            month = current_month - timedelta(days=30 * offset)
            month = month.replace(day=1)
            inc = Transaction.objects.filter(
                user=user,
                type='income',
                date__year=month.year,
                date__month=month.month,
            ).aggregate(total=Sum('amount'))['total'] or 0
            exp = Transaction.objects.filter(
                user=user,
                type='expense',
                date__year=month.year,
                date__month=month.month,
            ).aggregate(total=Sum('amount'))['total'] or 0
            semestral.append({
                'month': month.strftime('%b/%y'),
                'income': inc,
                'expense': exp,
                'balance': inc - exp,
            })

        context = {
            'categories': Category.objects.filter(user=user).order_by('name'),
            'category_expenses': category_expenses,
            'line_labels': json.dumps(months),
            'line_income': json.dumps(incomes),
            'line_expense': json.dumps(expenses),
            'line_balance': json.dumps(balances),
            'semestral': semestral,
        }
        return render(request, 'pages/relatorios.html', context)


class MetasView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def get(self, request, *args, **kwargs):
        user = request.user
        ensure_default_categories(user)

        goals = Goal.objects.filter(user=user).prefetch_related('deposit_set').order_by('-created_at')
        for goal in goals:
            goal.recent_deposits = goal.deposit_set.all()[:5]
        
        goals_ativas = [goal for goal in goals if not goal.is_completed]
        goals_concluidas = [goal for goal in goals if goal.is_completed]
        
        total_saved = sum([goal.current_amount for goal in goals_ativas])
        total_target = sum([goal.target_amount for goal in goals_ativas])
        completed = len(goals_concluidas)

        context = {
            'categories': Category.objects.filter(user=user).order_by('name'),
            'goals_ativas': goals_ativas,
            'goals_concluidas': goals_concluidas,
            'goal_count': len(goals_ativas),
            'total_saved': total_saved,
            'total_target': total_target,
            'completed_count': completed,
        }
        return render(request, 'pages/metas.html', context)


class AlertasView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def get(self, request, *args, **kwargs):
        user = request.user
        ensure_default_categories(user)
        refresh_alerts(user)

        unread = Alert.objects.filter(user=user, read=False).order_by('-created_at')
        read = Alert.objects.filter(user=user, read=True).order_by('-created_at')[:10]

        context = {
            'categories': Category.objects.filter(user=user).order_by('name'),
            'unread_alerts': unread,
            'read_alerts': read,
        }
        return render(request, 'pages/alertas.html', context)


class SaveGoalView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, *args, **kwargs):
        data = {}
        if request.content_type and request.content_type.startswith('application/json'):
            try:
                data = json.loads((request.body or b'{}').decode('utf-8'))
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Payload inválido.'}, status=400)
        else:
            data = request.POST.dict()

        icon = data.get('icon', '🎯')
        name = data.get('name', '').strip()
        target_amount = Decimal(data.get('target_amount') or 0)
        deadline = data.get('deadline')

        if not name or target_amount <= 0:
            return JsonResponse({'success': False, 'error': 'Nome ou valor alvo inválido.'}, status=400)

        Goal.objects.create(
            user=request.user,
            name=name,
            icon=icon,
            target_amount=target_amount,
            deadline=deadline or None,
        )
        return JsonResponse({'success': True})


class DepositGoalView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, *args, **kwargs):
        data = {}
        if request.content_type and request.content_type.startswith('application/json'):
            try:
                data = json.loads((request.body or b'{}').decode('utf-8'))
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Payload inválido.'}, status=400)
        else:
            data = request.POST.dict()

        goal_id = data.get('goal_id')
        deposit_amount = Decimal(data.get('deposit_amount') or 0)

        if not goal_id or deposit_amount <= 0:
            return JsonResponse({'success': False, 'error': 'ID da meta ou valor do depósito inválido.'}, status=400)

        goal = get_object_or_404(Goal, id=goal_id, user=request.user)
        
        if goal.current_amount + deposit_amount > goal.target_amount:
            return JsonResponse({'success': False, 'error': 'O depósito excederia o valor alvo da meta.'}, status=400)
        
        goal.current_amount += deposit_amount
        goal.save()

        # Create deposit record
        from .models import Deposit
        Deposit.objects.create(
            user=request.user,
            goal=goal,
            amount=deposit_amount,
        )

        # Create transaction to reduce balance
        poupanca_category = Category.objects.filter(user=request.user, name='Poupança').first()
        if not poupanca_category:
            poupanca_category = Category.objects.create(
                user=request.user,
                name='Poupança',
                icon='💰',
            )

        Transaction.objects.create(
            user=request.user,
            amount=deposit_amount,
            description=f'Depósito na meta: {goal.name}',
            date=timezone.localdate(),
            category=poupanca_category,
            type='expense',
        )

        return JsonResponse({'success': True})


class UpdateDepositView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        try:
            from .models import Deposit
            deposit = get_object_or_404(Deposit, id=pk, user=request.user)
            goal = deposit.goal
            
            data = {}
            if request.content_type and request.content_type.startswith('application/json'):
                data = json.loads((request.body or b'{}').decode('utf-8'))
            else:
                data = request.POST.dict()

            new_amount = Decimal(str(data.get('amount') or 0).replace(',', '.'))
            new_date = data.get('date')
            goal_id = data.get('goal_id')

            if new_amount <= 0:
                return JsonResponse({'success': False, 'error': 'Valor do depósito inválido.'}, status=400)

            # Calcular diferença
            difference = new_amount - deposit.amount
            
            # Verificar se não excede o target
            if goal.current_amount + difference > goal.target_amount:
                return JsonResponse({'success': False, 'error': 'O depósito excederia o valor alvo da meta.'}, status=400)

            # Verificar se não fica negativo
            if goal.current_amount + difference < 0:
                return JsonResponse({'success': False, 'error': 'O valor não pode deixar o progresso da meta negativo.'}, status=400)

            # Atualizar goal current_amount
            goal.current_amount += difference
            goal.save()

            # Atualizar deposit
            deposit.amount = new_amount
            if new_date and new_date.strip():
                try:
                    deposit.date = datetime.strptime(new_date.strip(), '%Y-%m-%d').date()
                except ValueError as e:
                    return JsonResponse({'success': False, 'error': 'Data inválida.'}, status=400)
            deposit.save()

            # Se houve diferença, ajustar a transação
            if difference != 0:
                poupanca_category = Category.objects.filter(user=request.user, name='Poupança').first()
                if not poupanca_category:
                    poupanca_category = Category.objects.create(
                        user=request.user,
                        name='Poupança',
                        icon='💰',
                    )
                Transaction.objects.create(
                    user=request.user,
                    amount=abs(difference),
                    description=f'Ajuste de depósito na meta: {goal.name}',
                    date=deposit.date,
                    category=poupanca_category,
                    type='expense' if difference > 0 else 'income',
                )

            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': 'Erro interno do servidor.'}, status=500)


class DeleteDepositView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        try:
            from .models import Deposit
            deposit = get_object_or_404(Deposit, id=pk, user=request.user)
            goal = deposit.goal

            # Subtrair o valor do depósito do current_amount da meta
            goal.current_amount -= deposit.amount
            if goal.current_amount < 0:
                goal.current_amount = 0
            goal.save()

            # Criar transação para ajustar o saldo (receita, pois está revertendo o depósito)
            poupanca_category = Category.objects.filter(user=request.user, name='Poupança').first()
            if not poupanca_category:
                poupanca_category = Category.objects.create(
                    user=request.user,
                    name='Poupança',
                    icon='💰',
                )
            Transaction.objects.create(
                user=request.user,
                amount=deposit.amount,
                description=f'Reversão de depósito na meta: {goal.name}',
                date=deposit.date,
                category=poupanca_category,
                type='income',
            )

            # Deletar o depósito
            deposit.delete()

            return JsonResponse({'success': True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': 'Erro interno do servidor.'}, status=500)


class UpdateGoalView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        goal = get_object_or_404(Goal, id=pk, user=request.user)
        
        data = {}
        if request.content_type and request.content_type.startswith('application/json'):
            try:
                data = json.loads((request.body or b'{}').decode('utf-8'))
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Payload inválido.'}, status=400)
        else:
            data = request.POST.dict()

        icon = data.get('icon', goal.icon)
        name = data.get('name', '').strip()
        target_amount = Decimal(data.get('target_amount') or 0)
        deadline = data.get('deadline')

        if not name or target_amount <= 0:
            return JsonResponse({'success': False, 'error': 'Nome ou valor alvo inválido.'}, status=400)

        goal.name = name
        goal.icon = icon
        goal.target_amount = target_amount
        goal.deadline = deadline or None
        goal.save()
        
        return JsonResponse({'success': True})


class DeleteGoalView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        goal = get_object_or_404(Goal, id=pk, user=request.user)
        
        # Somar os valores depositados para reverter ao saldo
        total_deposited = goal.deposit_set.aggregate(total=Sum('amount'))['total'] or 0
        
        # Criar transação de receita para reverter o saldo
        if total_deposited > 0:
            poupanca_category = Category.objects.filter(user=request.user, name='Poupança').first()
            if not poupanca_category:
                poupanca_category = Category.objects.create(
                    user=request.user,
                    name='Poupança',
                    icon='💰',
                )
            Transaction.objects.create(
                user=request.user,
                amount=total_deposited,
                description=f'Reversão de depósitos da meta excluída: {goal.name}',
                date=timezone.localdate(),
                category=poupanca_category,
                type='income',
            )
        
        goal.delete()
        return JsonResponse({'success': True})


class MarkAlertsReadView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, *args, **kwargs):
        Alert.objects.filter(user=request.user, read=False).update(read=True)
        return JsonResponse({'success': True})


class AddTransactionView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, *args, **kwargs):
        data = {}
        if request.content_type and request.content_type.startswith('application/json'):
            try:
                data = json.loads((request.body or b'{}').decode('utf-8'))
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Payload inválido.'}, status=400)
        else:
            data = request.POST.dict()

        transaction_type = data.get('type', 'expense')
        if transaction_type not in ['expense', 'income']:
            return JsonResponse({'success': False, 'error': 'Tipo de transação inválido.'}, status=400)

        category_id = data.get('category', 0)
        
        # Para receitas, se não tiver categoria, usa a primeira disponível
        if transaction_type == 'income' and (not category_id or category_id == ''):
            category = Category.objects.filter(user=request.user).first()
            if not category:
                ensure_default_categories(request.user)
                category = Category.objects.filter(user=request.user).first()
        else:
            # Para despesas, categoria é obrigatória
            try:
                category = get_object_or_404(Category, id=int(category_id), user=request.user)
            except (TypeError, ValueError):
                return JsonResponse({'success': False, 'error': 'Categoria inválida.'}, status=400)

        amount = data.get('amount')
        date = data.get('date')
        description = data.get('description', '').strip()
        if not amount or not date or not description:
            return JsonResponse({'success': False, 'error': 'Campos obrigatórios ausentes.'}, status=400)

        Transaction.objects.create(
            user=request.user,
            amount=Decimal(amount),
            description=description,
            date=date,
            category=category,
            type=transaction_type,
        )
        return JsonResponse({'success': True})
