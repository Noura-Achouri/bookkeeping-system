from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Record(models.Model):
    INCOME = 'income'
    EXPENSE = 'expense'

    TYPE_CHOICES = [
        (INCOME, 'Income'),
        (EXPENSE, 'Expense'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Null is enabled so no default value is assigned to old rows
    main_category = models.ForeignKey('categories.MainCategory', on_delete=models.SET_NULL, null=True, blank=True)
    subcategory = models.ForeignKey('categories.SubCategory', on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    remarks = models.TextField(blank=True)
    # Optional longer-form notes; blank on all existing rows.
    notes = models.TextField(blank=True, default='')
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.date})"