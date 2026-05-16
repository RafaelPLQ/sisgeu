from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone

from app.models import RecurringTransaction, Transaction
from app.recurring_logic import occurrence_date_for_today
from app.views import normalize_income_source, refresh_alerts

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Cria lançamentos a partir das transações recorrentes ativas '
        '(executar diariamente via agendador de tarefas ou cron).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default='',
            help='Data de referência YYYY-MM-DD (padrão: hoje no fuso do Django).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Somente mostra o que seria criado, sem gravar.',
        )

    def handle(self, *args, **options):
        raw = (options.get('date') or '').strip()
        if raw:
            today = datetime.strptime(raw, '%Y-%m-%d').date()
        else:
            today = timezone.localdate()

        dry = options['dry_run']
        created = 0
        users_touched = set()

        qs = RecurringTransaction.objects.filter(is_active=True).select_related(
            'user', 'category'
        )

        for rec in qs:
            occ = occurrence_date_for_today(rec, today)
            if occ is None:
                continue
            exists = Transaction.objects.filter(
                user=rec.user,
                recurring=rec,
                date=occ,
            ).exists()
            if exists:
                continue

            if dry:
                self.stdout.write(
                    f'[dry-run] {rec.description} — usuário {rec.user_id} — em {occ}'
                )
                created += 1
                continue

            with db_transaction.atomic():
                Transaction.objects.create(
                    user=rec.user,
                    amount=rec.amount,
                    description=rec.description,
                    date=occ,
                    category=rec.category,
                    type=rec.type,
                    income_source=(
                        normalize_income_source(rec.income_source)
                        if rec.type == 'income'
                        else ''
                    ),
                    recurring=rec,
                )
            users_touched.add(rec.user_id)
            created += 1

        for uid in users_touched:
            refresh_alerts(User.objects.get(pk=uid))

        if dry:
            self.stdout.write(
                self.style.WARNING(f'Dry-run: {created} lançamento(s) seriam criados.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Lançamentos automáticos criados: {created}')
            )
