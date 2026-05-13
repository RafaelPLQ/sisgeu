import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from app.models import Budget
from datetime import datetime

month = datetime(2026, 5, 1).date()
budgets = Budget.objects.filter(month=month)

print("Budgets salvos para Maio/2026:")
for b in budgets:
    print(f"  Category: {b.category}, Amount: {b.amount}, Allocation %: {b.allocation_percent}")
