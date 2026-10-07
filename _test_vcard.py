"""Quick check that the 3D payment card renders with both themes and correct content."""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django

django.setup()

from django.contrib.auth.models import User
from django.test import Client

USERNAME = 'zz_vcard_user'
PASSWORD = 'VcardPass123!'
failures = []


def check(label, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    print(f'  [{status}] {label}{(" :: " + str(detail)) if detail and not condition else ""}')
    if not condition:
        failures.append(label)


# Seed data so the dashboard renders the non-empty branch (stats + card area)
from categories.models import MainCategory
from records.models import Record

User.objects.filter(username=USERNAME).delete()
u = User.objects.create_user(USERNAME, 'zz_vcard@example.com', PASSWORD, first_name='Noura', last_name='Achouri')
cat = MainCategory.objects.create(name='Food', user=u)
Record.objects.create(user=u, main_category=cat, transaction_type=Record.EXPENSE, amount=42.5)

c = Client(SERVER_NAME='localhost')
check('login', c.login(username=USERNAME, password=PASSWORD))
r = c.get('/dashboard/')
body = r.content.decode('utf-8', 'ignore')

check('dashboard 200', r.status_code == 200)
check('3D card present', 'vcard3d' in body)
check('card scene', 'vcardScene' in body)
check('hero grid', 'dash-hero' in body)
check('card number', '**** **** **** 4821' in body)
check('card holder name', 'NOURA ACHOURI' in body)
check('valid thru', '09/29' in body)
check('brand name', 'BOOKKEEPER' in body)
check('chip', 'vcard-chip' in body)
check('contactless svg', 'vcard-contactless' in body)
check('payment brand circles', 'vcard-brand' in body)
check('depth layer', 'vcard-depth' in body)
check('glare layer', 'vcard-glare' in body)
check('tilt JS', 'vcardScene' in body and 'pointermove' in body)
check('reduced motion guard', 'prefers-reduced-motion' in body)
check('dark green theme', '#0E5F3F' in body)
check('light blue theme', 'A5F3FC' in body)
check('existing stats intact', 'data-countup' in body and 'stat-grid' in body)
check('existing promo intact', 'promo-card' in body and 'card-stack' in body)
check('existing trend chart intact', 'trendChart' in body)

User.objects.filter(username=USERNAME).delete()
print('\n======================================')
if failures:
    print(f'{len(failures)} FAILURES')
    raise SystemExit(1)
print('ALL CHECKS PASSED')
