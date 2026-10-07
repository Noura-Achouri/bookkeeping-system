"""Temporary end-to-end check for the UI redesign. Creates a throwaway user,
exercises every page and CRUD flow, then removes the data it created.
"""

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django

django.setup()

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from categories.models import MainCategory, SubCategory
from records.models import Record

USERNAME = 'zz_verify_user'
EMAIL = 'zz_verify@example.com'
PASSWORD = 'VerifyPass123!'

failures = []


def check(label, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    print(f'  [{status}] {label}{(" :: " + detail) if detail and not condition else ""}')
    if not condition:
        failures.append(label)


# ---------------------------------------------------------------- setup
User.objects.filter(username=USERNAME).delete()
user = User.objects.create_user(USERNAME, EMAIL, PASSWORD)
user.first_name = 'Verify'
user.last_name = 'User'
user.save()

client = Client(SERVER_NAME='localhost')
check('client login', client.login(username=USERNAME, password=PASSWORD))


def body_of(url):
    response = client.get(url)
    return response, response.content.decode('utf-8', 'ignore')


print('\n== Default categories on registration ==')
check('default categories created', MainCategory.objects.filter(user=user).count() == 5,
      str(MainCategory.objects.filter(user=user).count()))

print('\n== Empty states ==')
# Default categories are auto-created for new users; clear them to test the
# true empty state on the categories page.
MainCategory.objects.filter(user=user).delete()
for url, needle in [
    ('/dashboard/', 'Welcome to BookKeeper'),
    ('/records/', 'No financial records yet'),
    ('/categories/', 'No categories yet'),
    ('/reports/', 'Not enough data yet'),
]:
    response, body = body_of(url)
    check(f'GET {url} 200', response.status_code == 200, str(response.status_code))
    check(f'GET {url} empty state', needle in body)

print('\n== Public pages ==')
anon_public = Client(SERVER_NAME='localhost')
for url, needle in [
    ('/', 'BookKeeper'),
    ('/home/', 'BookKeeper'),
    ('/login/', 'Welcome back'),
    ('/register/', 'Create your account'),
]:
    response = anon_public.get(url)
    body = response.content.decode('utf-8', 'ignore')
    check(f'GET {url} 200', response.status_code == 200, str(response.status_code))
    check(f'GET {url} content', needle in body)
    check(f'GET {url} split layout', 'split-side' in body or 'landing-wrap' in body)

# login page specifics
login_response = anon_public.get('/login/')
login_body = login_response.content.decode('utf-8', 'ignore')
check('login has remember me', 'remember_me' in login_body)
check('login has forgot password', 'forgot_password' not in login_body and 'Forgot password?' in login_body)
check('login hidden field next', 'name="next"' not in login_body or 'csrfmiddlewaretoken' in login_body)

# register specifics
register_body = anon_public.get('/register/').content.decode('utf-8', 'ignore')
check('register has name field', 'name="username"' in register_body)
check('register has confirm password', 'name="password2"' in register_body)

print('\n== Seed data ==')
today = timezone.localdate()
food = MainCategory.objects.create(name='Food', user=user)
groceries = SubCategory.objects.create(name='Groceries', main_category=food, user=user)
salary = MainCategory.objects.create(name='Salary', user=user)
for index in range(4):
    Record.objects.create(
        user=user, main_category=food, subcategory=groceries,
        transaction_type=Record.EXPENSE, amount=50 + index * 10,
        remarks=f'Groceries run {index}', date=today - timedelta(days=index * 11),
    )
Record.objects.create(
    user=user, main_category=salary, transaction_type=Record.INCOME,
    amount=2500, remarks='Monthly salary', date=today - timedelta(days=5),
)
check('seed records created', Record.objects.filter(user=user).count() == 5)

print('\n== Records page ==')
response, body = body_of('/records/')
check('records stats cards', all(x in body for x in ['Total Income', 'Total Expense', 'Net Balance', 'Transactions']))
check('records shows entry', 'Groceries run 0' in body)
check('records add modal', 'addRecordModal' in body and 'Save Transaction' in body)
check('records edit modal', 'editRecordModal' in body)
check('records delete modal', 'deleteRecordModal' in body)
check('records type pill green/red', 'pill income' in body and 'pill expense' in body)
check('records currency symbol', '$' in body)

for query, needle, label in [
    ('?q=Monthly', 'Monthly salary', 'search text'),
    ('?type=income', 'Monthly salary', 'filter income'),
    ('?type=expense&category=%d' % food.id, 'Groceries run 1', 'filter category'),
    ('?sort=amount_low', 'Groceries run 0', 'sort amount asc'),
    ('?q=zzznomatch', 'No matching transactions', 'no-match empty state'),
]:
    response, body = body_of('/records/' + query)
    check(f'records {label}', response.status_code == 200 and needle in body)

print('\n== Categories page ==')
response, body = body_of('/categories/')
check('categories 200', response.status_code == 200)
check('categories cards', 'Food' in body and 'Salary' in body)
check('categories icon', '🍔' in body)
check('categories progress bar', 'data-width=' in body)
check('categories sub chip', 'Groceries' in body)
check('categories modals', all(x in body for x in ['createCategoryModal', 'editCategoryModal', 'editSubModal', 'deleteCategoryModal']))

print('\n== Reports page ==')
for rng in ['week', 'month', 'quarter', 'year']:
    response, body = body_of('/reports/?range=' + rng)
    check(f'reports range={rng}', response.status_code == 200 and 'Income vs Expense' in body)
response, body = body_of(f'/reports/?range=custom&start_date={today - timedelta(days=40)}&end_date={today}')
check('reports custom range', response.status_code == 200 and 'Income vs Expense' in body)
response, body = body_of('/reports/')
check('reports charts present', all(x in body for x in ['incomeExpenseChart', 'categoryChart', 'trendChart']))
check('reports savings progress', 'Savings Progress' in body)
check('reports export csv link', '/reports/export/' in body)

response = client.get('/reports/export/?range=year')
check('reports CSV export 200', response.status_code == 200)
check('reports CSV content type', response['Content-Type'].startswith('text/csv'))
csv_text = response.content.decode('utf-8')
check('reports CSV rows', 'Total Income' in csv_text and 'Monthly salary' in csv_text)

print('\n== Profile / Settings ==')
response, body = body_of('/profile/')
check('profile 200', response.status_code == 200)
check('profile hero', 'My Profile' in body and 'Verify User' in body)
check('profile tabs', all(x in body for x in ['Personal Information', 'Security', 'Preferences']))
check('profile password modal', 'passwordModal' in body)
check('profile buttons', 'Edit Profile' in body and 'Change Password' in body)

response, body = body_of('/settings/')
check('settings 200', response.status_code == 200)
check('settings sections', all(x in body for x in ['Appearance', 'Currency', 'Notifications', 'Account']))
check('settings toggles', body.count('class="switch') >= 4)
check('settings currency options', 'USD' in body and 'EUR' in body and 'MAD' in body)

print('\n== CRUD: records ==')
before = Record.objects.filter(user=user).count()
response = client.post('/records/add/', {
    'transaction_type': 'expense', 'amount': '77.50', 'date': today.isoformat(),
    'main_category': food.id, 'subcategory': groceries.id,
    'remarks': 'Modal added', 'notes': 'note text',
})
check('add record redirect', response.status_code == 302)
check('add record created', Record.objects.filter(user=user).count() == before + 1)
created = Record.objects.filter(user=user).order_by('-id').first()
check('add record notes saved', created.notes == 'note text')

response = client.post(f'/records/edit/{created.id}/', {
    'transaction_type': 'income', 'amount': '99.99', 'date': today.isoformat(),
    'main_category': salary.id, 'subcategory': '', 'remarks': 'Edited', 'notes': 'edited note',
})
created.refresh_from_db()
check('edit record redirect', response.status_code == 302)
check('edit record amount', str(created.amount) == '99.99')
check('edit record type', created.transaction_type == 'income')
check('edit record notes', created.notes == 'edited note')

response, body = body_of(f'/records/edit/{created.id}/')
check('edit record standalone page', response.status_code == 200 and 'Edit Transaction' in body)

response = client.post(f'/records/delete/{created.id}/')
check('delete record redirect', response.status_code == 302)
check('delete record removed', not Record.objects.filter(id=created.id).exists())

response, body = body_of('/records/add/')
check('add record standalone page', response.status_code == 200 and 'New Transaction' in body)

print('\n== CRUD: categories ==')
new_main = None
response = client.post('/categories/add/', {'name': 'Travel', 'category_type': 'main'})
check('add category redirect', response.status_code == 302)
new_main = MainCategory.objects.filter(user=user, name='Travel').first()
check('add category created', new_main is not None)

response = client.post('/categories/add/', {'name': 'Flights', 'category_type': 'sub', 'main_category': new_main.id})
check('add subcategory created', SubCategory.objects.filter(user=user, name='Flights').exists())

response = client.post(f'/categories/edit/main/{new_main.id}/', {'name': 'Travel & Trips'})
new_main.refresh_from_db()
check('edit category renamed', new_main.name == 'Travel & Trips')

flights = SubCategory.objects.get(user=user, name='Flights')
response = client.post(f'/categories/edit/sub/{flights.id}/', {'name': 'Airfare', 'main_category': food.id})
flights.refresh_from_db()
check('edit subcategory renamed', flights.name == 'Airfare')
check('edit subcategory reparented', flights.main_category_id == food.id)

response, body = body_of(f'/categories/delete/main/{new_main.id}/')
check('delete category page', response.status_code == 200 and 'Travel & Trips' in body)
response = client.post(f'/categories/delete/main/{new_main.id}/')
check('delete category removed', not MainCategory.objects.filter(id=new_main.id).exists())
check('delete category page 200', client.get('/categories/add/').status_code == 200)

print('\n== CRUD: account ==')
response = client.post('/profile/update/', {
    'first_name': 'Verified', 'last_name': 'Person',
    'username': USERNAME, 'email': EMAIL,
})
user.refresh_from_db()
check('update profile redirect', response.status_code == 302)
check('update profile saved', user.first_name == 'Verified' and user.last_name == 'Person')

response = client.post('/profile/password/', {
    'old_password': PASSWORD, 'new_password1': 'NewVerifyPass456!', 'new_password2': 'NewVerifyPass456!',
})
check('change password redirect', response.status_code == 302)
PASSWORD = 'NewVerifyPass456!'
check('change password works', client.login(username=USERNAME, password=PASSWORD))

response = client.post('/settings/update/', {
    'currency': 'EUR', 'notify_transactions': 'on', 'notify_reports': 'on',
})
check('update settings redirect', response.status_code == 302)
response, body = body_of('/settings/')
check('settings currency persisted', 'value="EUR" selected' in body)
response, body = body_of('/records/')
check('currency applied to records', '€' in body)

response = client.post('/settings/update/', {'currency': 'USD'})
check('currency reset', client.get('/records/').content.decode('utf-8').count('$') > 0)

print('\n== Language switching ==')
response = client.post('/i18n/setlang/', {'language': 'fr', 'next': '/records/'}, follow=True)
body = response.content.decode('utf-8', 'ignore')
check('french records page', 'Écritures financières' in body)
response = client.post('/i18n/setlang/', {'language': 'ar', 'next': '/records/'}, follow=True)
check('arabic records page', 'السجلات المالية' in response.content.decode('utf-8', 'ignore'))
response = client.post('/i18n/setlang/', {'language': 'zh-hans', 'next': '/reports/'}, follow=True)
check('chinese reports page', '收入与支出' in response.content.decode('utf-8', 'ignore'))
response = client.post('/i18n/setlang/', {'language': 'ber', 'next': '/profile/'}, follow=True)
check('amazigh profile page', 'Ammud-iw' in response.content.decode('utf-8', 'ignore'))
client.post('/i18n/setlang/', {'language': 'en', 'next': '/'})

print('\n== Security / access ==')
anon = Client(SERVER_NAME='localhost')
for url in ['/dashboard/', '/records/', '/categories/', '/reports/', '/profile/', '/settings/']:
    response = anon.get(url)
    check(f'anon {url} redirected', response.status_code == 302 and '/login/' in response['Location'])

# ---------------------------------------------------------------- cleanup
User.objects.filter(username=USERNAME).delete()
check('cleanup: user removed', not User.objects.filter(username=USERNAME).exists())
check('cleanup: records removed', Record.objects.filter(user__username=USERNAME).count() == 0)
check('cleanup: categories removed', MainCategory.objects.filter(user__username=USERNAME).count() == 0)

print('\n======================================')
if failures:
    print(f'{len(failures)} FAILURES:')
    for name in failures:
        print('   -', name)
    sys.exit(1)
print('ALL CHECKS PASSED')
