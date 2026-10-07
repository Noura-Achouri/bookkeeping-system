from django import template
from django.utils.safestring import mark_safe
from ..translations import TRANSLATIONS

register = template.Library()


def _resolve_lang(context):
    """Figure out which language to use for this template render.

    Priority order:
    1. The active language set by LocaleMiddleware (``LANGUAGE_CODE`` context var).
    2. The session's chosen language (``_language``).
    3. Default to ``en``.
    """
    lang = None
    if 'LANGUAGE_CODE' in context:
        lang = context['LANGUAGE_CODE']
    if not lang:
        request = context.get('request')
        if request is not None:
            lang = request.session.get('_language')
    return lang or 'en'


def _resolve(context, key, kwargs, safe=True):
    lang = _resolve_lang(context)
    bundle = TRANSLATIONS.get(lang) or TRANSLATIONS['en']
    text = bundle.get(key) or TRANSLATIONS['en'].get(key, key)
    if kwargs:
        try:
            text = text % kwargs
        except (KeyError, ValueError):
            pass
    if safe:
        return mark_safe(text)
    return text


@register.simple_tag(takes_context=True)
def lang_text(context, key, **kwargs):
    """Look up ``key`` in the active language's translation bundle.

    Returned strings are marked safe so translations can include inline HTML
    like ``<strong>`` without needing ``{% autoescape off %}`` everywhere.
    """
    return _resolve(context, key, kwargs)


# Aliases so existing templates can keep using the familiar ``trans`` /
# ``blocktrans`` / ``_`` syntax while still pulling from our dictionary.
@register.simple_tag(takes_context=True, name='trans')
def trans(context, key, **kwargs):
    return _resolve(context, key, kwargs)


@register.simple_tag(takes_context=True, name='blocktrans')
def blocktrans(context, key, **kwargs):
    return _resolve(context, key, kwargs)


@register.simple_tag(takes_context=True)
def lang_attr(context, key):
    """``mark_safe`` variant of lang_text, useful for inline JS strings."""
    return mark_safe(_resolve(context, key, {}))


@register.filter
def get_item(mapping, key):
    """Dictionary lookup filter: ``mapping|get_item:key``."""
    try:
        return mapping[key]
    except (KeyError, TypeError):
        return None