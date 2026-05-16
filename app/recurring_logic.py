"""Lógica de datas para transações recorrentes (mensal / semanal)."""
import calendar
from datetime import date


def monthly_due_date(year: int, month: int, due_day: int) -> date:
    """Retorna o dia de vencimento no mês, limitado ao último dia do mês."""
    _, last = calendar.monthrange(year, month)
    day = min(int(due_day), last)
    return date(year, month, day)


def occurrence_date_for_today(rec, today: date) -> date | None:
    """
    Se `today` for o dia de gerar o lançamento desta recorrência, retorna essa data.
    Caso contrário, None.
    """
    if not rec.is_active or today < rec.start_date:
        return None

    if rec.frequency == 'monthly':
        target = monthly_due_date(today.year, today.month, rec.due_day)
        if target == today:
            return target
        return None

    if rec.frequency == 'weekly':
        if today.weekday() == rec.due_day:
            return today
        return None

    return None
