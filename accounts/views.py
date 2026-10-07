
# Create your views here.
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.urls import reverse
from .forms import RegisterForm, ProfileForm, AvatarForm
from .models import UserProfile
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone

from records.models import Record
from django.db.models import Sum
from core.context_processors import CURRENCIES

def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            users_group, created = Group.objects.get_or_create(name='Users')
            user.groups.add(users_group)

            # Log the user in immediately after registration
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(request, username=user.username, password=raw_password)
            if user is not None:
                login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None
    username = ''

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # "Remember me" unchecked -> session ends when the browser closes.
            if not request.POST.get('remember_me'):
                request.session.set_expiry(0)

            # Redirect to the page the user originally requested, if any.
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect('dashboard')

        error = 'Invalid username or password.'

    return render(request, 'login.html', {
        'error': error,
        'username': username,
        'next': request.GET.get('next', ''),
    })

@login_required
def dashboard(request):
    records = Record.objects.filter(user=request.user)

    income = records.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or 0

    expense = records.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or 0

    balance = income - expense

    # Get recently used categories from records
    from categories.models import MainCategory
    recent_categories = MainCategory.objects.filter(user=request.user).order_by('-created_at')[:4]

    # Recent records ordered by transaction date
    recent_records = records.order_by('-date', '-created_at')[:5]

    # Monthly income/expense trend (last 6 months)
    today = timezone.now().date()
    month_labels = []
    income_series = []
    expense_series = []
    for i in range(5, -1, -1):
        # compute proper month boundaries (i months before current month)
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        label = timezone.datetime(year, month, 1).strftime('%b %Y')
        month_labels.append(label)

        month_income = records.filter(
            transaction_type='income',
            date__year=year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0

        month_expense = records.filter(
            transaction_type='expense',
            date__year=year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0

        income_series.append(float(month_income))
        expense_series.append(float(month_expense))

    # Category expense breakdown
    category_breakdown = records.filter(
        transaction_type='expense',
        main_category__isnull=False
    ).values('main_category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:6]

    category_colors = ['#10B981', '#34D399', '#059669', '#6EE7B7', '#A7F3D0', '#D1FAE5']
    category_pairs = [
        {
            'label': c['main_category__name'],
            'value': float(c['total']),
            'color': category_colors[i % len(category_colors)]
        }
        for i, c in enumerate(category_breakdown)
    ]

    return render(request, 'dashboard.html', {
        'income': income,
        'expense': expense,
        'balance': balance,
        'records': recent_records,
        'recent_categories': recent_categories,
        'month_labels': month_labels,
        'income_series': income_series,
        'expense_series': expense_series,
        'category_labels': [c['main_category__name'] for c in category_breakdown],
        'category_series': [float(c['total']) for c in category_breakdown],
        'category_pairs': category_pairs,
    })


def user_logout(request):
    logout(request)
    return redirect('login')


# ---------------------------------------------------------------------------
# Profile / Account
# ---------------------------------------------------------------------------

def _profile_context(request, profile_form=None, password_form=None, open_password_modal=False):
    """Everything the Profile page needs, in one place."""
    from categories.models import MainCategory

    record_count = Record.objects.filter(user=request.user).count()
    category_count = MainCategory.objects.filter(user=request.user).count()
    user_profile = UserProfile.objects.filter(user=request.user).first()

    return {
        'profile_form': profile_form or ProfileForm(instance=request.user),
        'password_form': password_form or PasswordChangeForm(request.user),
        'open_password_modal': open_password_modal,
        'avatar_form': AvatarForm(instance=user_profile),
        'avatar': user_profile.avatar if user_profile and user_profile.avatar else None,
        'avatar_errors': None,
        'total_records': record_count,
        'total_categories': category_count,
    }


@login_required
def profile(request):
    return render(request, 'profile.html', _profile_context(request))


@login_required
def update_avatar(request):
    """Upload or replace the profile photo from the Profile page."""
    if request.method != 'POST':
        return redirect('profile')

    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    # Capture the old file name BEFORE validation: ModelForm._post_clean
    # overwrites instance.avatar with the newly uploaded file.
    old_name = user_profile.avatar.name if user_profile.avatar else None
    form = AvatarForm(request.POST, request.FILES, instance=user_profile)
    if form.is_valid():
        profile_obj = form.save()
        # Remove the previous file so stale uploads don't pile up.
        if old_name and profile_obj.avatar and profile_obj.avatar.name != old_name:
            default_storage.delete(old_name)
        return redirect(f"{reverse('profile')}?saved=avatar")

    context = _profile_context(request)
    context['avatar_errors'] = [str(e) for errors in form.errors.values() for e in errors]
    return render(request, 'profile.html', context)


@login_required
def remove_avatar(request):
    """Delete the profile photo and fall back to the default avatar."""
    if request.method != 'POST':
        return redirect('profile')

    user_profile = UserProfile.objects.filter(user=request.user).first()
    if user_profile and user_profile.avatar:
        user_profile.avatar.delete(save=False)
        user_profile.avatar = None
        user_profile.save(update_fields=['avatar'])
    return redirect(f"{reverse('profile')}?removed=avatar")


@login_required
def update_profile(request):
    if request.method != 'POST':
        return redirect('profile')

    form = ProfileForm(request.POST, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect(f"{reverse('profile')}?saved=profile")

    return render(request, 'profile.html', _profile_context(request, profile_form=form))


@login_required
def change_password(request):
    if request.method != 'POST':
        return redirect('profile')

    form = PasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        # Keep the user logged in after their password changes.
        update_session_auth_hash(request, user)
        return redirect(f"{reverse('profile')}?saved=password")

    return render(
        request,
        'profile.html',
        _profile_context(request, password_form=form, open_password_modal=True),
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@login_required
def settings_view(request):
    return render(request, 'settings.html')


@login_required
def update_settings(request):
    if request.method != 'POST':
        return redirect('settings')

    currency = request.POST.get('currency')
    if currency in CURRENCIES:
        request.session['currency'] = currency

    request.session['notify_transactions'] = request.POST.get('notify_transactions') == 'on'
    request.session['notify_reports'] = request.POST.get('notify_reports') == 'on'
    request.session['notify_reminders'] = request.POST.get('notify_reminders') == 'on'

    return redirect(f"{reverse('settings')}?saved=1")
