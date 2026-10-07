import os
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django

django.setup()

from core.translations import TRANSLATIONS

en = TRANSLATIONS['en']
pattern = re.compile(r"lang_text\s+['\"]([A-Za-z0-9_]+)['\"]")

used = set()
for root, dirs, files in os.walk('templates'):
    for name in files:
        if not name.endswith('.html'):
            continue
        text = open(os.path.join(root, name), encoding='utf-8').read()
        used |= set(pattern.findall(text))

missing = sorted(used - set(en))
print('keys used in templates :', len(used))
print('keys in en bundle      :', len(en))
print('missing from en        :', len(missing))
for key in missing:
    print('   -', key)

# Also report keys missing from each non-English bundle
for lang, bundle in TRANSLATIONS.items():
    if lang == 'en':
        continue
    gap = sorted(set(en) - set(bundle))
    print(f'{lang}: {len(gap)} keys falling back to English')
    for key in gap:
        print('   ~', key)
