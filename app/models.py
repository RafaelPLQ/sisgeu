from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, blank=True, help_text="Emoji ou ícone")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"


class RecurringTransaction(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', 'Mensal'),
        ('weekly', 'Semanal'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=[('income', 'Receita'), ('expense', 'Despesa')])
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    income_source = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Para receitas: Salário, Bolsa, etc.',
    )
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    due_day = models.PositiveSmallIntegerField(
        help_text='Mensal: dia 1–31. Semanal: 0=segunda … 6=domingo (padrão Python).',
    )
    start_date = models.DateField(help_text='A partir desta data a recorrência passa a gerar lançamentos.')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} ({self.get_frequency_display()})"

    def due_summary(self):
        if self.frequency == 'monthly':
            return f'Dia {self.due_day}'
        weekdays = ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')
        if 0 <= self.due_day < 7:
            return f'Toda {weekdays[self.due_day]}'
        return f'Índice {self.due_day}'

    class Meta:
        verbose_name = "Transação recorrente"
        verbose_name_plural = "Transações recorrentes"
        ordering = ['description']


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('income', 'Receita'),
        ('expense', 'Despesa'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    income_source = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Para receitas: Salário, Bolsa, etc. (independente da categoria contábil)',
    )
    recurring = models.ForeignKey(
        RecurringTransaction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='generated_transactions',
    )

    def __str__(self):
        return f"{self.description} - R$ {self.amount}"

    class Meta:
        verbose_name = "Transação"
        verbose_name_plural = "Transações"
        ordering = ['-date']


class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.DateField(help_text="Mês de referência (ex: 2023-03-01)")

    def __str__(self):
        return f"{self.category.name} - R$ {self.amount} ({self.month.strftime('%m/%Y')})"

    class Meta:
        verbose_name = "Orçamento"
        verbose_name_plural = "Orçamentos"
        unique_together = ['user', 'category', 'month']


class Goal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    icon = models.CharField(max_length=10, default='🎯')
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Meta"
        verbose_name_plural = "Metas"

    def __str__(self):
        return self.name

    @property
    def progress_percent(self):
        if self.target_amount <= 0:
            return 0
        return min(100, float((self.current_amount or 0) / self.target_amount * 100))

    @property
    def is_completed(self):
        return self.current_amount >= self.target_amount


class Deposit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Depósito"
        verbose_name_plural = "Depósitos"
        ordering = ['-date']

    def __str__(self):
        return f"Depósito de R$ {self.amount} em {self.goal.name}"


class Alert(models.Model):
    ALERT_TYPES = [
        ('orcamento_80', 'Orçamento 80%'),
        ('orcamento_100', 'Orçamento 100%'),
        ('meta_prazo', 'Meta com Prazo'),
        ('saldo_negativo', 'Saldo Negativo'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    goal = models.ForeignKey(Goal, on_delete=models.SET_NULL, null=True, blank=True)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    title = models.CharField(max_length=150)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        unique_together = ['user', 'alert_type', 'category', 'goal']

    def __str__(self):
        return f"{self.title} ({self.user})"
 
