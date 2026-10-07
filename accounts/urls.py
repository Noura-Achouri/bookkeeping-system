from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    # Profile / account
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/avatar/', views.update_avatar, name='update_avatar'),
    path('profile/avatar/remove/', views.remove_avatar, name='remove_avatar'),
    path('profile/password/', views.change_password, name='change_password'),
    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/update/', views.update_settings, name='update_settings'),
]
