"""Financial reports / analytics center.

Everything here is read-only: it derives charts and headline numbers from the
records the user already has. No models were added, so the existing data flow
is untouched.
"""

import csv
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from records.models import Record


RANGE_OPTIONS = ('week', 'month', 'quarter', 'year', 'custom')

# A restrained palette: mostly emerald/teal greens with a couple of cool
# accents so the charts feel financial rather than neon.
CHART_COLORS = [
    '#00FF41', '#10B981', '#059669', '#14B8A6',
    '#0EA5E9', '#6366F1', '#8B5CF6', '#F59E0B',
]

SAVINGS_TARGET = 20  # % of income we nudge the user towards.


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _resolve_range(request):
    """Return (range_key, start_date, end_date) for the requested period."""
    today = timezone.localdate()
    range_key = request.GET.get('range') or 'month'
    if range_key not in RANGE_OPTIONS:
        range_key = 'month'

    if range_key == 'week':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif range_key == 'month':
        start = today.replace(day=1)
        end = today
    elif range_key == 'quarter':
        start = today - timedelta(days=90)
        end = today
    elif range_key == 'year':
        start = today.replace(month=1, day=1)
        end = today
    else:
        start = _parse_date(request.GET.get('start_date')) or today.replace(day=1)
        end = _parse_date(request.GET.get('end_date')) or today

    if start > end:
        start, end = end, start

    return range_key, start, end


def _month_span(start, end):
    """Ordered list of (year, month) tuples covering the range."""
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


def _month_label(year, month):
    return date(year, month, 1).strftime('%b %Y')


def _totals(qs):
    income = Decimal('0')
    expense = Decimal('0')
    for row in qs:
        if row['transaction_type'] == Record.INCOME:
            income += row['amount']
        else:
            expense += row['amount']
    return income, expense


@login_required
def report_view(request):
    range_key, start, end = _resolve_range(request)

    today = timezone.localdate()
    days = max((min(end, today) - start).days + 1, 1)

    rows = list(
        Record.objects.filter(user=request.user, date__gte=start, date__lte=end)
        .values('date', 'transaction_type', 'amount', 'main_category__name')
    )

    income, expense = _totals(rows)
    net = income - expense
    savings_rate = float(net / income * 100) if income else 0

    # --- Monthly income / expense series -----------------------------------
    months = _month_span(start, end)
    month_index = {m: i for i, m in enumerate(months)}
    income_series = [0.0] * len(months)
    expense_series = [0.0] * len(months)
    net_series = [0.0] * len(months)

    for row in rows:
        idx = month_index.get((row['date'].year, row['date'].month))
        if idx is None:
            continue
        if row['transaction_type'] == Record.INCOME:
            income_series[idx] += float(row['amount'])
        else:
            expense_series[idx] += float(row['amount'])

    net_series = [round(i - e, 2) for i, e in zip(income_series, expense_series)]
    income_series = [round(v, 2) for v in income_series]
    expense_series = [round(v, 2) for v in expense_series]
    month_labels = [_month_label(y, m) for y, m in months]

    # --- Spending by category ----------------------------------------------
    category_totals = {}
    for row in rows:
        if row['transaction_type'] != Record.EXPENSE:
            continue
        name = row['main_category__name'] or ''
        category_totals[name] = category_totals.get(name, 0) + float(row['amount'])

    ranked = sorted(category_totals.items(), key=lambda kv: kv[1], reverse=True)
    category_rows = [
        {
            'label': name,
            'value': round(value, 2),
            'percent': round(value / float(expense) * 100, 1) if expense else 0,
            'color': CHART_COLORS[i % len(CHART_COLORS)],
        }
        for i, (name, value) in enumerate(ranked)
    ]

    # --- Headline analytics -------------------------------------------------
    tracked_days = max(days, 1)
    daily_average = float(expense) / tracked_days
    net_by_month = list(zip(month_labels, net_series))
    highest_month = max(net_by_month, key=lambda m: m[1]) if net_by_month else (None, 0)
    lowest_month = min(net_by_month, key=lambda m: m[1]) if net_by_month else (None, 0)

    # --- Previous period comparison ----------------------------------------
    span = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span - 1)
    prev_rows = list(
        Record.objects.filter(
            user=request.user, date__gte=prev_start, date__lte=prev_end
        ).values('transaction_type', 'amount')
    )
    prev_income, prev_expense = _totals(prev_rows)
    prev_net = prev_income - prev_expense
    has_previous = bool(prev_rows)

    def delta(current, previous):
        if not previous:
            return None
        return round(float((current - previous) / previous * 100), 1)

    return render(request, 'reports.html', {
        'range_key': range_key,
        'start_date': start,
        'end_date': end,
        'range_days': days,
        'income': income,
        'expense': expense,
        'net': net,
        'savings_rate': round(savings_rate, 1),
        'savings_progress': max(0.0, min(100.0, round(savings_rate, 1))),
        'savings_target': SAVINGS_TARGET,
        'total_count': len(rows),
        'has_data': bool(rows),
        'month_labels': month_labels,
        'income_series': income_series,
        'expense_series': expense_series,
        'net_series': net_series,
        'category_rows': category_rows,
        'category_labels': [c['label'] for c in category_rows],
        'category_series': [c['value'] for c in category_rows],
        'category_colors': [c['color'] for c in category_rows],
        'daily_average': round(daily_average, 2),
        'highest_month': highest_month,
        'lowest_month': lowest_month,
        'avg_monthly_expense': round(float(expense) / max(len(months), 1), 2),
        'income_delta': delta(income, prev_income),
        'expense_delta': delta(expense, prev_expense),
        'net_delta': delta(net, prev_net) if prev_income or prev_expense else None,
        'has_previous': has_previous,
        'filters': {
            'range': range_key,
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
        },
    })


@login_required
def export_report(request):
    """Stream the filtered records as a CSV download."""
    _, start, end = _resolve_range(request)
    qs = (
        Record.objects.filter(user=request.user, date__gte=start, date__lte=end)
        .select_related('main_category', 'subcategory')
        .order_by('date', 'id')
    )

    filename = f'bookkeeper-report-{start.isoformat()}-{end.isoformat()}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Subcategory', 'Description', 'Amount'])

    total_income = Decimal('0')
    total_expense = Decimal('0')

    for record in qs:
        if record.transaction_type == Record.INCOME:
            total_income += record.amount
        else:
            total_expense += record.amount

        writer.writerow([
            record.date.isoformat(),
            record.get_transaction_type_display(),
            record.main_category.name if record.main_category else '',
            record.subcategory.name if record.subcategory else '',
            (record.remarks or '').replace('\n', ' '),
            f'{record.amount:.2f}',
        ])

    writer.writerow([])
    writer.writerow(['Total Income', f'{total_income:.2f}'])
    writer.writerow(['Total Expenses', f'{total_expense:.2f}'])
    writer.writerow(['Net Balance', f'{total_income - total_expense:.2f}'])

    return response
