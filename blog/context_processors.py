from django.conf import settings

from .models import Category


def site_chrome(request):
    """Values every page needs: site identity and the topic navigation."""
    return {
        "site_name": settings.SITE_NAME,
        "site_tagline": settings.SITE_TAGLINE,
        "site_description": settings.SITE_DESCRIPTION,
        "nav_categories": Category.objects.all()[:12],
    }
