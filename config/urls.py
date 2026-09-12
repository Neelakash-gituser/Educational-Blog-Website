from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.static import serve

from blog.feeds import LatestPostsFeed
from blog.sitemaps import CategorySitemap, PostSitemap, StaticSitemap

sitemaps = {
    "posts": PostSitemap,
    "categories": CategorySitemap,
    "static": StaticSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("feed/", LatestPostsFeed(), name="post_feed"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("", include("blog.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    # static() is a no-op outside DEBUG, so wire the serve view up explicitly.
    urlpatterns += [
        re_path(
            r"^%s(?P<path>.*)$" % settings.MEDIA_URL.lstrip("/"),
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]

handler404 = "blog.views.page_not_found"
handler500 = "blog.views.server_error"
