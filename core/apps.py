from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """Make ``check_for_language`` accept every code declared in
        ``settings.LANGUAGES``.

        Django 5+ only allows a language change when a ``.mo`` file exists for
        the language. We don't ship gettext catalogs (our translations live in
        :mod:`core.translations`), so we patch the check to also accept the
        codes we registered. Without this, switching to Amazigh (``ber``) or
        any locale without a compiled catalog silently falls back to
        ``LANGUAGE_CODE``.
        """
        from django.conf import settings
        from django.utils import translation

        valid_codes = {code for code, _ in getattr(settings, 'LANGUAGES', [])}

        original = translation.check_for_language

        def patched(lang_code):
            if lang_code in valid_codes:
                return True
            return original(lang_code)

        # ``trans_real.check_for_language`` is what ``translation`` re-exports
        # and what the cookie path invokes. Patch both to be safe.
        translation.check_for_language = patched
        try:
            from django.utils.translation import trans_real
            trans_real.check_for_language = patched
        except ImportError:
            pass