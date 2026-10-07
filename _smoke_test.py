import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth.models import User

c = Client(HTTP_HOST='localhost')
r = c.get('/')
html = r.content.decode('utf-8', errors='ignore')
print('landing:', r.status_code, '| cards removed:', 'credit-card' not in html)

from categories.models import MainCategory
from records.models import Record

u, created = User.objects.get_or_create(username='smoketest')
if created:
    u.set_password('Test12345!')
    u.save()
c.login(username='smoketest', password='Test12345!')

# Seed one record so the dashboard renders the non-empty branch (with promo card)
Record.objects.filter(user=u).delete()
cat = MainCategory.objects.filter(user=u).first()
if cat is None:
    cat = MainCategory.objects.create(name='Smoke', user=u)
Record.objects.create(user=u, main_category=cat, transaction_type=Record.INCOME, amount=100)

r = c.get('/dashboard/')
html = r.content.decode('utf-8', errors='ignore')
print('dashboard:', r.status_code, '| card-stack present:', 'card-stack' in html,
      '| user name on card:', 'SMOKETEST' in html)
print('light override present:', '[data-theme="light"] .credit-card' in html)
u.delete()
