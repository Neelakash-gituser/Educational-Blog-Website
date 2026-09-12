from urllib.parse import quote, urlencode

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Rebuild the current query string with some parameters changed.

    Used by pagination and filter chips so they keep the active search term.
    """
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    if "page" not in kwargs:
        # Changing a filter should send the reader back to the first page.
        params.pop("page", None)
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else ""


@register.filter
def urlencode_value(value):
    return quote(str(value or ""), safe="")


@register.simple_tag
def share_links(url, title):
    """Share URLs for the post page, built without any third-party script."""
    return {
        "x": "https://twitter.com/intent/tweet?" + urlencode({"url": url, "text": title}),
        "linkedin": "https://www.linkedin.com/sharing/share-offsite/?" + urlencode({"url": url}),
        "reddit": "https://reddit.com/submit?" + urlencode({"url": url, "title": title}),
        "hn": "https://news.ycombinator.com/submitlink?" + urlencode({"u": url, "t": title}),
        "mail": "mailto:?" + urlencode({"subject": title, "body": url}),
    }


@register.filter
def avatar_or_initials(profile):
    """Either an <img> for the uploaded avatar, or a coloured initials badge."""
    if profile and getattr(profile, "avatar", None) and profile.avatar:
        return mark_safe(
            f'<img src="{profile.avatar.url}" alt="" class="avatar-img" loading="lazy">'
        )
    initials = profile.initials if profile else "?"
    hue = (sum(ord(c) for c in initials) * 37) % 360
    return mark_safe(
        f'<span class="avatar-initials" style="--avatar-hue: {hue}">{initials}</span>'
    )


@register.filter
def pluralise(count, forms="post,posts"):
    singular, plural = forms.split(",")
    return singular if count == 1 else plural
