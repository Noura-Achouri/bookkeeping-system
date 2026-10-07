from django.urls import path
from . import views

urlpatterns = [
    path('', views.records_list, name='records'),
    path('add/', views.add_record, name='add_record'),
    path('edit/<int:pk>/', views.edit_record, name='edit_record'),
    path('delete/<int:pk>/', views.delete_record, name='delete_record'),
    path('get-subcategories/', views.get_subcategories, name='get_subcategories'),
]