from django.urls import path
from . import views

urlpatterns = [
    path('', views.category_list, name='category_list'),
    path('add/', views.add_category, name='add_category'),
    path('edit/<str:category_type>/<int:category_id>/', views.edit_category, name='edit_category'),
    path('delete/<str:category_type>/<int:category_id>/', views.delete_category, name='delete_category'),
]
