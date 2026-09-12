from django.conf import settings
from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Rss201rev2Feed

from .models import Post


class LatestPostsFeed(Feed):
    feed_type = Rss201rev2Feed
    description_template = None

    @property
    def title(self):
        return settings.SITE_NAME

    @property
    def description(self):
        return settings.SITE_DESCRIPTION

    def link(self):
        return reverse("blog:home")

    def items(self):
        return Post.objects.published().with_related()[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt

    def item_pubdate(self, item):
        return item.published_at

    def item_author_name(self, item):
        return item.author.profile.name

    def item_categories(self, item):
        names = [tag.name for tag in item.tags.all()]
        return ([item.category.name] if item.category else []) + names
