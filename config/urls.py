from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect, render
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from core.views import set_language

def home(request):
    """Site root: send logged-in users to the dashboard, everyone else to the landing page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html', {'is_landing': True})

def landing(request):
    """Dedicated landing page, always reachable at /home/ whether or not you are logged in."""
    return render(request, 'landing.html', {'is_landing': True})

def custom_404(request, exception):
    return render(request, '404.html', status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('home/', landing, name='landing'),
    path('', include('accounts.urls')),
    path('records/', include('records.urls')),
    path('categories/', include('categories.urls')),
    path('reports/', include('reports.urls')),
    path('categories/', include('categories.urls')),
    path('i18n/setlang/', set_language, name='set_language'),
]

# Serve user-uploaded media files in development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = custom_404