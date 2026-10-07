"""Lightweight UI preferences exposed to every template.

Currency and notification choices are kept in the user's session so that no
database migration is required and the existing data flow stays untouched.
Defaults reproduce the previous hard-coded behaviour (US dollar, notifications
on) so nothing changes for users who never open the Settings page.
"""

CURRENCIES = {
    'USD': {'symbol': '$', 'label': 'US Dollar', 'code': 'USD'},
    'EUR': {'symbol': '€', 'label': 'Euro', 'code': 'EUR'},
    'GBP': {'symbol': '£', 'label': 'British Pound', 'code': 'GBP'},
    'CNY': {'symbol': '¥', 'label': 'Chinese Yuan', 'code': 'CNY'},
    'MAD': {'symbol': 'DH', 'label': 'Moroccan Dirham', 'code': 'MAD'},
}

DEFAULT_CURRENCY = 'USD'


def ui_preferences(request):
    """Expose the active currency + notification flags to templates."""
    session = getattr(request, 'session', None)

    code = DEFAULT_CURRENCY
    notify_transactions = True
    notify_reports = True
    notify_reminders = False

    if session is not None:
        code = session.get('currency', DEFAULT_CURRENCY)
        notify_transactions = session.get('notify_transactions', True)
        notify_reports = session.get('notify_reports', True)
        notify_reminders = session.get('notify_reminders', False)

    if code not in CURRENCIES:
        code = DEFAULT_CURRENCY

    return {
        'currency_code': code,
        'currency_symbol': CURRENCIES[code]['symbol'],
        'currency_options': CURRENCIES,
        'notify_transactions': notify_transactions,
        'notify_reports': notify_reports,
        'notify_reminders': notify_reminders,
    }
