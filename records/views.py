from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from .models import Record
from .forms import RecordForm
from categories.models import MainCategory, SubCategory


SORT_OPTIONS = {
    'newest': ('-date', '-created_at'),
    'oldest': ('date', 'created_at'),
    'amount_high': ('-amount', '-date'),
    'amount_low': ('amount', '-date'),
}


@login_required
def records_list(request):
    records = Record.objects.filter(user=request.user).select_related(
        'main_category', 'subcategory'
    )

    transaction_type = request.GET.get('type')
    category_id = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    query = (request.GET.get('q') or '').strip()
    sort = request.GET.get('sort') or 'newest'
    if sort not in SORT_OPTIONS:
        sort = 'newest'

    if transaction_type in ('income', 'expense'):
        records = records.filter(transaction_type=transaction_type)
    if category_id:
        records = records.filter(main_category_id=category_id)
    if start_date:
        records = records.filter(date__gte=start_date)
    if end_date:
        records = records.filter(date__lte=end_date)
    if query:
        search = (
            Q(remarks__icontains=query)
            | Q(main_category__name__icontains=query)
            | Q(subcategory__name__icontains=query)
        )
        try:
            search |= Q(amount=Decimal(query))
        except (InvalidOperation, ValueError):
            pass
        records = records.filter(search)

    records = records.order_by(*SORT_OPTIONS[sort])

    income = records.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or 0
    expense = records.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or 0
    balance = income - expense

    categories = MainCategory.objects.filter(user=request.user)

    return render(request, 'records.html', {
        'records': records,
        'total_count': records.count(),
        'categories': categories,
        'income': income,
        'expense': expense,
        'balance': balance,
        'has_filters': bool(transaction_type or category_id or start_date or end_date or query),
        'filters': {
            'type': transaction_type or '',
            'category': category_id or '',
            'start_date': start_date or '',
            'end_date': end_date or '',
            'q': query,
            'sort': sort,
        },
    })


@login_required
def add_record(request):
    if request.method == 'POST':
        form = RecordForm(request.user, request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.user = request.user
            record.save()
            return redirect('records')
    else:
        form = RecordForm(user=request.user)

    return render(request, 'add_record.html', {'form': form})


@login_required
def edit_record(request, pk):
    record = get_object_or_404(Record, pk=pk, user=request.user)

    if request.method == 'POST':
        form = RecordForm(request.user, request.POST, instance=record)
        if form.is_valid():
            form.save()
            return redirect('records')
    else:
        form = RecordForm(user=request.user, instance=record)

    return render(request, 'edit_record.html', {'form': form, 'record': record})


@login_required
def delete_record(request, pk):
    record = get_object_or_404(Record, pk=pk, user=request.user)

    if request.method == 'POST':
        record.delete()
        return redirect('records')

    return render(request, 'delete_record.html', {'record': record})


@login_required
def get_subcategories(request):
    main_id = request.GET.get('main_id')
    subs = SubCategory.objects.filter(main_category_id=main_id, user=request.user)
    data = [{'id': s.id, 'name': s.name} for s in subs]
    return JsonResponse({'subcategories': data})