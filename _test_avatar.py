"""End-to-end test for the editable profile photo feature."""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django

django.setup()

import sys
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from accounts.models import UserProfile

USERNAME = 'zz_avatar_user'
PASSWORD = 'AvatarPass123!'
failures = []


def check(label, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    print(f'  [{status}] {label}{(" :: " + str(detail)) if detail and not condition else ""}')
    if not condition:
        failures.append(label)


def make_image(name='avatar.png', color=(0, 164, 230)):
    buf = BytesIO()
    Image.new('RGB', (300, 300), color).save(buf, format='PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


# ---- setup
User.objects.filter(username=USERNAME).delete()
user = User.objects.create_user(USERNAME, 'zz_avatar@example.com', PASSWORD)
client = Client(SERVER_NAME='localhost')
check('login', client.login(username=USERNAME, password=PASSWORD))

print('\n== Profile page renders ==')
response = client.get('/profile/')
body = response.content.decode('utf-8', 'ignore')
check('profile 200', response.status_code == 200)
check('default avatar shown', '/static/images/default_profile.png' in body)
check('avatar edit button', 'avatar-edit-btn' in body)
check('avatar modal', 'avatarModal' in body)
check('avatar upload form', '/profile/avatar/' in body and 'multipart/form-data' in body)
check('no remove button without avatar', 'Remove Photo' not in body)

print('\n== Upload avatar ==')
img1 = make_image('first.png')
response = client.post('/profile/avatar/', {'avatar': img1}, follow=True)
body = response.content.decode('utf-8', 'ignore')
check('upload redirect 200', response.status_code == 200)
profile = UserProfile.objects.get(user=user)
check('avatar saved', profile.avatar is not None and profile.avatar.name != '')
check('avatar file in media/avatars/', profile.avatar.name.startswith('avatars/'))
check('avatar shown on page', profile.avatar.url in body)
check('remove button now present', 'Remove Photo' in body)
check('success toast text', 'Profile photo updated.' in body)

print('\n== Replace avatar (old file cleaned up) ==')
old_name = profile.avatar.name
img2 = make_image('second.png', color=(124, 77, 255))
response = client.post('/profile/avatar/', {'avatar': img2}, follow=True)
profile.refresh_from_db()
new_name = profile.avatar.name
check('replacement saved', new_name != old_name)
media_root = django.conf.settings.MEDIA_ROOT
check('old file deleted', not (media_root / old_name).exists(), old_name)
check('new file exists', (media_root / new_name).exists(), new_name)

print('\n== Validation ==')
# The multipart parser recomputes file size from the bytes, so test the
# size limit at form level (the same validation the view relies on).
from accounts.forms import AvatarForm

fresh_user_profile = UserProfile.objects.filter(user=user).first()
big = make_image('big.png')
big.size = 6 * 1024 * 1024  # over the 5 MB limit
form = AvatarForm({}, {'avatar': big}, instance=fresh_user_profile)
check('oversize rejected', not form.is_valid(),
      dict(form.errors))
check('oversize message', any('smaller than 5 MB' in e for errs in form.errors.values() for e in errs))

empty_form = AvatarForm({}, {}, instance=None)
check('empty upload rejected', not empty_form.is_valid(),
      dict(empty_form.errors))
check('empty upload message', any('choose an image' in e for errs in empty_form.errors.values() for e in errs))

print('\n== Remove avatar ==')
current_name = UserProfile.objects.get(user=user).avatar.name
response = client.post('/profile/avatar/remove/', follow=True)
body = response.content.decode('utf-8', 'ignore')
profile = UserProfile.objects.get(user=user)
check('remove redirect 200', response.status_code == 200)
check('avatar cleared', profile.avatar is None or profile.avatar.name == '')
check('file deleted from disk', not (media_root / current_name).exists())
check('falls back to default', '/static/images/default_profile.png' in body)

print('\n== Cleanup ==')
User.objects.filter(username=USERNAME).delete()
check('user removed', not User.objects.filter(username=USERNAME).exists())

print('\n======================================')
if failures:
    print(f'{len(failures)} FAILURES:')
    for name in failures:
        print('   -', name)
    sys.exit(1)
print('ALL CHECKS PASSED')
