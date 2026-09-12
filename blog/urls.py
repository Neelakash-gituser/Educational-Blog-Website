from django.urls import path

from . import views

app_name = "blog"

urlpatterns = [
    path("", views.home, name="home"),
    path("articles/", views.post_list, name="post_list"),
    path("search/", views.search, name="search"),
    path("topics/", views.topic_index, name="topics"),
    path("topics/<slug:slug>/", views.category_detail, name="category"),
    path("tags/<slug:slug>/", views.tag_detail, name="tag"),
    path("authors/<str:username>/", views.author_detail, name="author"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("reading-list/", views.reading_list, name="reading_list"),
    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/new/", views.post_create, name="post_create"),
    path("dashboard/preview/", views.markdown_preview, name="markdown_preview"),
    path("dashboard/<slug:slug>/edit/", views.post_edit, name="post_edit"),
    path("dashboard/<slug:slug>/delete/", views.post_delete, name="post_delete"),
    path("dashboard/comments/<int:pk>/moderate/", views.comment_moderate, name="comment_moderate"),
    # Reader actions
    path("comments/<int:pk>/edit/", views.comment_edit, name="comment_edit"),
    path("comments/<int:pk>/delete/", views.comment_delete, name="comment_delete"),
    path("comments/<int:pk>/like/", views.comment_like, name="comment_like"),
    # Posts last: a bare slug should not shadow the routes above.
    path("<slug:slug>/", views.post_detail, name="post_detail"),
    path("<slug:slug>/comment/", views.comment_create, name="comment_create"),
    path("<slug:slug>/like/", views.post_like, name="post_like"),
    path("<slug:slug>/bookmark/", views.post_bookmark, name="post_bookmark"),
]
