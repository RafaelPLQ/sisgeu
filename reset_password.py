#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

u = User.objects.get(username='testuser')
u.set_password('test123')
u.save()
print('Senha redefinida para testuser: test123')
