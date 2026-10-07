from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.urls import reverse
from .models import MainCategory, SubCategory
from records.models import Record


# Emoji "icons" for well-known categories. Anything unknown falls back to a
# neutral folder so every card still gets a visual anchor.
CATEGORY_ICONS = {
    'food': '🍔',
    'dining': '🍔',
    'restaurant': '🍔',
    'grocer': '🛒',
    'transport': '🚗',
    'car': '🚗',
    'travel': '✈️',
    'housing': '🏠',
    'accommodation': '🏠',
    'rent': '🏠',
    'home': '🏠',
    'shopping': '🛍',
    'clothes': '🛍',
    'subscription': '💻',
    'entertainment': '🎬',
    'education': '🎓',
    'health': '💊',
    'medical': '💊',
    'salary': '💰',
    'income': '💰',
    'saving': '🏦',
    'bill': '🧾',
    'utilit': '💡',
    'other': '📦',
}

DEFAULT_ICON = '📁'


def _icon_for(name):
    key = (name or '').strip().lower()
    if key in CATEGORY_ICONS:
        return CATEGORY_ICONS[key]
    for token, icon in CATEGORY_ICONS.items():
        if token in key:
            return icon
    return DEFAULT_ICON


@login_required
def category_list(request):
    records = Record.objects.filter(user=request.user)

    total_expense = records.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or 0
    total_income = records.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or 0

    aggregates = records.values('main_category_id').annotate(
        transactions=Count('id'),
        expense=Sum('amount', filter=Q(transaction_type='expense')),
        income=Sum('amount', filter=Q(transaction_type='income')),
    )
    by_category = {row['main_category_id']: row for row in aggregates}

    main_categories = MainCategory.objects.filter(user=request.user).prefetch_related(
        'subcategory_set'
    ).order_by('name')

    category_stats = []
    for main in main_categories:
        row = by_category.get(main.id) or {}
        expense = row.get('expense') or 0
        income = row.get('income') or 0
        count = row.get('transactions') or 0
        percent = (float(expense) / float(total_expense) * 100) if total_expense else 0

        category_stats.append({
            'id': main.id,
            'name': main.name,
            'icon': _icon_for(main.name),
            'count': count,
            'expense': expense,
            'income': income,
            'total': expense + income,
            'percent': round(percent, 1),
            'subcategories': list(main.subcategory_set.all()),
        })

    # Biggest spenders first; unused categories fall to the end alphabetically.
    category_stats.sort(key=lambda c: (-float(c['expense']), c['name'].lower()))

    return render(request, 'category_list.html', {
        'main_categories': main_categories,
        'category_stats': category_stats,
        'total_expense': total_expense,
        'total_income': total_income,
        'category_count': len(category_stats),
        'total_transactions': records.count(),
    })


@login_required
def add_category(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        category_type = request.POST.get('category_type')
        main_category_id = request.POST.get('main_category')

        if name and category_type == 'main':
            MainCategory.objects.create(name=name, user=request.user)
        elif name and category_type == 'sub' and main_category_id:
            main = get_object_or_404(MainCategory, id=main_category_id, user=request.user)
            SubCategory.objects.create(name=name, main_category=main, user=request.user)

        return redirect(f"{reverse('category_list')}?saved=category")

    main_categories = MainCategory.objects.filter(user=request.user)
    return render(request, 'add_category.html', {
        'main_categories': main_categories
    })


@login_required
def edit_category(request, category_type, category_id):
    if category_type == 'main':
        category = get_object_or_404(MainCategory, id=category_id, user=request.user)
    else:
        category = get_object_or_404(SubCategory, id=category_id, user=request.user)

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        if name:
            category.name = name

        if category_type == 'sub':
            main_id = request.POST.get('main_category')
            if main_id:
                category.main_category = get_object_or_404(
                    MainCategory, id=main_id, user=request.user
                )

        category.save()
        return redirect(f"{reverse('category_list')}?saved=category")

    return redirect('category_list')


@login_required
def delete_category(request, category_type, category_id):
    if category_type == 'main':
        category = get_object_or_404(MainCategory, id=category_id, user=request.user)
    else:
        category = get_object_or_404(SubCategory, id=category_id, user=request.user)

    if request.method == 'POST':
        category.delete()
        return redirect(f"{reverse('category_list')}?saved=deleted")

    return render(request, 'delete_category.html', {
        'category': category
    })
