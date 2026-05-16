import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db.models import Max, Min, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Alert, Budget, Category, Goal, RecurringTransaction, Transaction
from .forms import CategoryForm

INCOME_SOURCE_CHOICES = frozenset({'Salário', 'Bolsa', 'Venda', 'Reembolso', 'Outros'})


def normalize_income_source(value):
    s = (value or '').strip()
    if s in INCOME_SOURCE_CHOICES:
        return s
    return 'Outros'


def get_month_start(d):
    return d.replace(day=1)


def iter_months_inclusive(start_month, end_month):
    """Percorre o 1º dia de cada mês de start_month até end_month (inclusive)."""
    y, m = start_month.year, start_month.month
    ey, em = end_month.year, end_month.month
    while (y, m) <= (ey, em):
        yield date(y, m, 1)
        if m == 12:
            m = 1
            y += 1
        else:
            m += 1


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

        recurring_list = (
            RecurringTransaction.objects.filter(user=user)
            .select_related('category')
            .order_by('description')
        )
        recurring_editor_data = [
            {
                'id': r.id,
                'description': r.description,
                'amount': str(r.amount),
                'type': r.type,
                'category_id': r.category_id,
                'income_source': r.income_source or 'Outros',
                'frequency': r.frequency,
                'due_day': r.due_day,
                'start_date': r.start_date.isoformat(),
                'is_active': r.is_active,
            }
            for r in recurring_list
        ]

        context = {
            'current_balance': current_balance,
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'budget_used_percent': total_percent,
            'recent_transactions': recent_transactions,
            'budget_usage': budget_usage,
            'categories': Category.objects.filter(user=user).order_by('name'),
            'recurring_list': recurring_list,
            'recurring_editor_data': recurring_editor_data,
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
        month_dates = list(all_transactions.dates('date', 'month', order='DESC'))

        context = {
            'categories': Category.objects.filter(user=user).order_by('name'),
            'income_transactions': income_transactions,
            'expense_transactions': expense_transactions,
            'filter_months': month_dates,
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
            total_budget += amount
            total_spent += spent
            icon = (category.icon or '').strip()
            orc_labels.append(f'{icon} {category.name}'.strip() if icon else category.name)
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

        bounds = Transaction.objects.filter(user=user).aggregate(
            first=Min('date'),
            last=Max('date'),
        )
        first_date = bounds['first']
        last_date = bounds['last']
        if first_date is None:
            start_month = current_month
            end_month = current_month
        else:
            start_month = get_month_start(first_date)
            end_month = max(current_month, get_month_start(last_date))

        month_totals = {}
        for row in (
            Transaction.objects.filter(user=user)
            .annotate(m=TruncMonth('date'))
            .values('m')
            .annotate(
                inc=Sum('amount', filter=Q(type='income')),
                exp=Sum('amount', filter=Q(type='expense')),
            )
        ):
            key_dt = row['m']
            month_totals[(key_dt.year, key_dt.month)] = row

        months = []
        incomes = []
        expenses = []
        balances = []
        semestral = []
        for month in iter_months_inclusive(start_month, end_month):
            months.append(month.strftime('%b/%y'))
            row = month_totals.get((month.year, month.month), {})
            inc = row.get('inc') if row.get('inc') is not None else Decimal('0')
            exp = row.get('exp') if row.get('exp') is not None else Decimal('0')
            incomes.append(float(inc))
            expenses.append(float(exp))
            balances.append(float(inc - exp))
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

        income_source = ''
        if transaction_type == 'income':
            income_source = normalize_income_source(data.get('extra') or data.get('income_source'))

        Transaction.objects.create(
            user=request.user,
            amount=Decimal(amount),
            description=description,
            date=date,
            category=category,
            type=transaction_type,
            income_source=income_source,
        )
        return JsonResponse({'success': True})


class UpdateTransactionView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        tx = get_object_or_404(Transaction, id=pk, user=request.user)
        data = {}
        if request.content_type and request.content_type.startswith('application/json'):
            try:
                data = json.loads((request.body or b'{}').decode('utf-8'))
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Payload inválido.'}, status=400)
        else:
            data = request.POST.dict()

        description = (data.get('description') or '').strip()
        amount_raw = data.get('amount')
        date_str = data.get('date')
        category_id = data.get('category')
        tx_type = data.get('type')

        if not description or amount_raw in (None, '') or not date_str:
            return JsonResponse({'success': False, 'error': 'Campos obrigatórios ausentes.'}, status=400)

        if tx_type not in ('income', 'expense') or tx_type != tx.type:
            return JsonResponse({'success': False, 'error': 'Tipo de lançamento inválido.'}, status=400)

        if tx_type == 'expense':
            try:
                category = get_object_or_404(Category, id=int(category_id), user=request.user)
            except (TypeError, ValueError):
                return JsonResponse({'success': False, 'error': 'Categoria inválida.'}, status=400)
        else:
            category = None

        try:
            amount = Decimal(str(amount_raw).strip().replace(',', '.'))
        except (InvalidOperation, AttributeError):
            return JsonResponse({'success': False, 'error': 'Valor inválido.'}, status=400)

        if amount <= 0:
            return JsonResponse({'success': False, 'error': 'O valor deve ser maior que zero.'}, status=400)

        try:
            parsed_date = datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Data inválida.'}, status=400)

        tx.description = description
        tx.amount = amount
        tx.date = parsed_date
        if tx_type == 'expense':
            tx.category = category
            tx.income_source = ''
        else:
            tx.income_source = normalize_income_source(data.get('income_source'))
        tx.save()

        return JsonResponse({'success': True})


class DeleteTransactionView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        tx = get_object_or_404(Transaction, id=pk, user=request.user)
        tx.delete()
        return JsonResponse({'success': True})


class SaveRecurringView(LoginRequiredMixin, View):
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

        user = request.user
        ensure_default_categories(user)

        description = (data.get('description') or '').strip()
        if not description:
            return JsonResponse({'success': False, 'error': 'Descrição obrigatória.'}, status=400)

        tx_type = data.get('type', 'expense')
        if tx_type not in ('income', 'expense'):
            return JsonResponse({'success': False, 'error': 'Tipo inválido.'}, status=400)

        frequency = data.get('frequency', 'monthly')
        if frequency not in ('monthly', 'weekly'):
            return JsonResponse({'success': False, 'error': 'Frequência inválida.'}, status=400)

        try:
            due_day = int(data.get('due_day'))
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': 'Dia de vencimento inválido.'}, status=400)

        if frequency == 'monthly' and not (1 <= due_day <= 31):
            return JsonResponse({'success': False, 'error': 'Mensal: escolha o dia entre 1 e 31.'}, status=400)
        if frequency == 'weekly' and not (0 <= due_day <= 6):
            return JsonResponse(
                {'success': False, 'error': 'Semanal: dia da semana de 0 (segunda) a 6 (domingo).'},
                status=400,
            )

        try:
            category = get_object_or_404(Category, id=int(data.get('category_id')), user=user)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': 'Categoria inválida.'}, status=400)

        try:
            amount = Decimal(str(data.get('amount')).strip().replace(',', '.'))
        except (InvalidOperation, TypeError, AttributeError):
            return JsonResponse({'success': False, 'error': 'Valor inválido.'}, status=400)
        if amount <= 0:
            return JsonResponse({'success': False, 'error': 'O valor deve ser maior que zero.'}, status=400)

        date_str = data.get('start_date')
        if not date_str:
            return JsonResponse({'success': False, 'error': 'Informe a data inicial.'}, status=400)
        try:
            start_date = datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Data inicial inválida.'}, status=400)

        is_active = data.get('is_active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() in ('1', 'true', 'yes', 'on')

        income_source = ''
        if tx_type == 'income':
            income_source = normalize_income_source(data.get('income_source'))

        pk = data.get('id') or data.get('pk')
        if pk:
            rec = get_object_or_404(RecurringTransaction, id=int(pk), user=user)
        else:
            rec = RecurringTransaction(user=user)

        rec.description = description
        rec.amount = amount
        rec.type = tx_type
        rec.category = category
        rec.income_source = income_source
        rec.frequency = frequency
        rec.due_day = due_day
        rec.start_date = start_date
        rec.is_active = bool(is_active)
        rec.save()

        return JsonResponse({'success': True, 'id': rec.id})


class DeleteRecurringView(LoginRequiredMixin, View):
    login_url = settings.LOGIN_URL

    def post(self, request, pk, *args, **kwargs):
        rec = get_object_or_404(RecurringTransaction, id=pk, user=request.user)
        rec.delete()
        return JsonResponse({'success': True})
