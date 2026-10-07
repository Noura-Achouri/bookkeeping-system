from django.urls import path
from .views import report_view, export_report

urlpatterns = [
    path('', report_view, name='reports'),
    path('export/', export_report, name='export_report'),
]
