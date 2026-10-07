"""Custom views for the core app.

The :func:`set_language` view is a small replacement for Django's built-in
``django.views.i18n.set_language``. Django 5+ checks whether a ``.mo`` file
exists before allowing a language change, which would block the Amazigh code
(``ber``) and any other locale for which we don't ship compiled message
catalogs. This view simply validates against ``settings.LANGUAGES`` and sets
the ``django_language`` cookie, no gettext files required.
"""
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.http import url_has_allowed_host_and_scheme

LANGUAGE_COOKIE_NAME = getattr(settings, 'LANGUAGE_COOKIE_NAME', 'django_language')


def set_language(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = request.META.get('HTTP_REFERER') or '/'
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = '/'

    response = HttpResponseRedirect(next_url) if next_url else HttpResponse(status=204)

    if request.method == 'POST':
        lang_code = request.POST.get('language')
        valid_codes = {code for code, _ in getattr(settings, 'LANGUAGES', [])}
        if lang_code and lang_code in valid_codes:
            response.set_cookie(
                LANGUAGE_COOKIE_NAME,
                lang_code,
                max_age=getattr(settings, 'LANGUAGE_COOKIE_AGE', 365 * 24 * 60 * 60),
                path=getattr(settings, 'LANGUAGE_COOKIE_PATH', '/'),
                domain=getattr(settings, 'LANGUAGE_COOKIE_DOMAIN', None),
                secure=getattr(settings, 'LANGUAGE_COOKIE_SECURE', False),
                httponly=getattr(settings, 'LANGUAGE_COOKIE_HTTPONLY', False),
                samesite=getattr(settings, 'LANGUAGE_COOKIE_SAMESITE', 'Lax'),
            )

    return response