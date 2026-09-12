"""Views for the public blog, the reader actions and the author dashboard."""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import mail_admins
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CommentForm, ContactForm, PostForm, SubscribeForm
from .markdown_utils import render_markdown
from .models import Category, Comment, Post, Subscriber, Tag

SORT_OPTIONS = {
    "recent": ("-published_at", "Newest"),
    "popular": ("-view_count", "Most read"),
    "discussed": ("-comment_total", "Most discussed"),
    "liked": ("-like_total", "Most liked"),
}


def _viewer_can_edit(user, post):
    return user.is_authenticated and (post.author_id == user.id or user.is_staff)


def _is_author(user):
    return user.is_authenticated and (
        user.is_staff or getattr(getattr(user, "profile", None), "can_write", False)
    )


def _paginate(request, queryset, per_page=None):
    paginator = Paginator(queryset, per_page or settings.PAGINATE_BY)
    return paginator.get_page(request.GET.get("page"))


def _post_feed(request, base_queryset):
    """Shared filtering/sorting used by every listing page."""
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "recent")
    if sort not in SORT_OPTIONS:
        sort = "recent"
    posts = base_queryset.with_related().with_counts().search(query)
    posts = posts.order_by(SORT_OPTIONS[sort][0], "-created_at")
    return posts, query, sort


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def home(request):
    published = Post.objects.published()
    featured = (
        published.with_related().with_counts().filter(is_featured=True).first()
        or published.with_related().with_counts().first()
    )
    latest = published.with_related().with_counts()
    if featured:
        latest = latest.exclude(pk=featured.pk)

    context = {
        "featured": featured,
        "latest_posts": latest[:6],
        "most_read": published.with_related().order_by("-view_count")[:5],
        "categories": Category.objects.annotate(
            total=Count(
                "posts",
                filter=Q(posts__status=Post.Status.PUBLISHED, posts__published_at__lte=timezone.now()),
            )
        ).filter(total__gt=0),
        "tags": Tag.objects.annotate(total=Count("posts")).filter(total__gt=0).order_by("-total")[:18],
        "total_posts": published.count(),
        "subscribe_form": SubscribeForm(),
    }
    return render(request, "blog/home.html", context)


def post_list(request):
    posts, query, sort = _post_feed(request, Post.objects.published())
    category_slug = request.GET.get("topic", "")
    active_category = None
    if category_slug:
        active_category = Category.objects.filter(slug=category_slug).first()
        if active_category:
            posts = posts.filter(category=active_category)

    context = {
        "page_obj": _paginate(request, posts),
        "query": query,
        "sort": sort,
        "sort_options": SORT_OPTIONS,
        "categories": Category.objects.all(),
        "active_category": active_category,
        "heading": "All articles",
        "subheading": "Everything published so far, newest first.",
    }
    return render(request, "blog/post_list.html", context)


def search(request):
    posts, query, sort = _post_feed(request, Post.objects.published())
    context = {
        "page_obj": _paginate(request, posts),
        "query": query,
        "sort": sort,
        "sort_options": SORT_OPTIONS,
        "categories": Category.objects.all(),
        "heading": f"Results for “{query}”" if query else "Search",
        "subheading": "Titles, bodies, tags, topics and authors are all searched.",
        "is_search": True,
    }
    return render(request, "blog/post_list.html", context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    posts, query, sort = _post_feed(
        request, Post.objects.published().filter(category=category)
    )
    context = {
        "page_obj": _paginate(request, posts),
        "query": query,
        "sort": sort,
        "sort_options": SORT_OPTIONS,
        "category": category,
        "categories": Category.objects.all(),
        "active_category": category,
        "heading": category.name,
        "subheading": category.tagline or category.description,
    }
    return render(request, "blog/post_list.html", context)


def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    posts, query, sort = _post_feed(request, Post.objects.published().filter(tags=tag))
    context = {
        "page_obj": _paginate(request, posts),
        "query": query,
        "sort": sort,
        "sort_options": SORT_OPTIONS,
        "tag": tag,
        "heading": f"#{tag.name}",
        "subheading": "Posts tagged with this label.",
    }
    return render(request, "blog/post_list.html", context)


def topic_index(request):
    categories = Category.objects.annotate(
        total=Count(
            "posts",
            filter=Q(posts__status=Post.Status.PUBLISHED, posts__published_at__lte=timezone.now()),
        )
    )
    context = {
        "categories": categories,
        "tags": Tag.objects.annotate(total=Count("posts")).filter(total__gt=0).order_by("-total"),
    }
    return render(request, "blog/topics.html", context)


def author_detail(request, username):
    author = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )
    posts, query, sort = _post_feed(request, Post.objects.published().filter(author=author))
    context = {
        "author": author,
        "author_profile": author.profile,
        "page_obj": _paginate(request, posts),
        "query": query,
        "sort": sort,
        "sort_options": SORT_OPTIONS,
        "post_total": Post.objects.published().filter(author=author).count(),
    }
    return render(request, "blog/author_detail.html", context)


def post_detail(request, slug):
    queryset = Post.objects.with_related().select_related("author__profile")
    post = get_object_or_404(queryset, slug=slug)

    if not post.is_published and not _viewer_can_edit(request.user, post):
        # Unpublished posts are invisible to everyone but their author.
        from django.http import Http404

        raise Http404("No post found")

    if post.is_published and not _viewer_can_edit(request.user, post):
        seen = request.session.setdefault("seen_posts", [])
        if post.pk not in seen:
            post.register_view()
            post.view_count += 1
            request.session["seen_posts"] = (seen + [post.pk])[-200:]
            request.session.modified = True

    comments = (
        post.comments.filter(is_approved=True, parent__isnull=True)
        .select_related("author", "author__profile")
        .prefetch_related("replies__author__profile", "likes", "replies__likes")
    )

    context = {
        "post": post,
        "comments": comments,
        "comment_form": CommentForm(),
        "comment_count": post.comment_count(),
        "related_posts": post.related_posts(),
        "can_edit": _viewer_can_edit(request.user, post),
        "has_liked": request.user.is_authenticated and post.likes.filter(pk=request.user.pk).exists(),
        "has_bookmarked": request.user.is_authenticated
        and post.bookmarks.filter(pk=request.user.pk).exists(),
        "like_count": post.likes.count(),
        "share_url": request.build_absolute_uri(post.get_absolute_url()),
        "moderation_on": settings.COMMENT_MODERATION,
    }
    return render(request, "blog/post_detail.html", context)


# --------------------------------------------------------------------------- #
# Reader actions
# --------------------------------------------------------------------------- #


@login_required
@require_POST
def comment_create(request, slug):
    post = get_object_or_404(Post.objects.published(), slug=slug)
    if not post.allow_comments:
        messages.error(request, "Comments are closed on this post.")
        return redirect(post.get_absolute_url())

    form = CommentForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors.get("body", ["That comment could not be posted."])[0])
        return redirect(f"{post.get_absolute_url()}#comments")

    comment = form.save(commit=False)
    comment.post = post
    comment.author = request.user
    parent_id = request.POST.get("parent")
    if parent_id:
        comment.parent = post.comments.filter(pk=parent_id).first()
    comment.is_approved = not settings.COMMENT_MODERATION
    comment.save()

    if comment.is_approved:
        messages.success(request, "Comment posted.")
        anchor = f"#comment-{comment.pk}"
    else:
        messages.info(request, "Thanks! Your comment is awaiting moderation.")
        anchor = "#comments"
    return redirect(f"{post.get_absolute_url()}{anchor}")


@login_required
@require_POST
def comment_delete(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=pk)
    if comment.author_id != request.user.id and not request.user.is_staff:
        return HttpResponseBadRequest("Not your comment.")
    url = comment.post.get_absolute_url()
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect(f"{url}#comments")


@login_required
@require_POST
def comment_edit(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=pk)
    if comment.author_id != request.user.id:
        return HttpResponseBadRequest("Not your comment.")
    form = CommentForm(request.POST, instance=comment)
    if form.is_valid():
        edited = form.save(commit=False)
        edited.is_edited = True
        edited.save()
        messages.success(request, "Comment updated.")
    else:
        messages.error(request, "That edit could not be saved.")
    return redirect(f"{comment.post.get_absolute_url()}#comment-{comment.pk}")


@login_required
@require_POST
def comment_like(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=pk)
    if comment.likes.filter(pk=request.user.pk).exists():
        comment.likes.remove(request.user)
        liked = False
    else:
        comment.likes.add(request.user)
        liked = True
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"liked": liked, "count": comment.likes.count()})
    return redirect(f"{comment.post.get_absolute_url()}#comment-{comment.pk}")


@login_required
@require_POST
def post_like(request, slug):
    post = get_object_or_404(Post.objects.published(), slug=slug)
    if post.likes.filter(pk=request.user.pk).exists():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"liked": liked, "count": post.likes.count()})
    return redirect(post.get_absolute_url())


@login_required
@require_POST
def post_bookmark(request, slug):
    post = get_object_or_404(Post.objects.published(), slug=slug)
    if post.bookmarks.filter(pk=request.user.pk).exists():
        post.bookmarks.remove(request.user)
        saved = False
    else:
        post.bookmarks.add(request.user)
        saved = True
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"saved": saved})
    messages.success(request, "Saved to your reading list." if saved else "Removed from your reading list.")
    return redirect(post.get_absolute_url())


@login_required
def reading_list(request):
    posts = (
        request.user.bookmarked_posts.published().with_related().with_counts().order_by("-published_at")
    )
    return render(request, "blog/reading_list.html", {"page_obj": _paginate(request, posts)})


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #


@login_required
def dashboard(request):
    if not _is_author(request.user):
        return render(request, "dashboard/not_an_author.html", status=403)

    mine = Post.objects.filter(author=request.user).with_related().with_counts()
    status = request.GET.get("status", "all")
    if status in {Post.Status.DRAFT, Post.Status.PUBLISHED}:
        mine = mine.filter(status=status)

    context = {
        "page_obj": _paginate(request, mine.order_by("-updated_at"), per_page=12),
        "status": status,
        "counts": {
            "all": Post.objects.filter(author=request.user).count(),
            "published": Post.objects.filter(author=request.user).published().count(),
            "draft": Post.objects.filter(author=request.user).drafts().count(),
        },
        "totals": {
            "views": Post.objects.filter(author=request.user).aggregate(n=Sum("view_count"))["n"] or 0,
            "comments": Comment.objects.filter(post__author=request.user, is_approved=True).count(),
            "likes": Post.objects.filter(author=request.user).aggregate(n=Count("likes"))["n"],
        },
        "pending_comments": Comment.objects.filter(
            post__author=request.user, is_approved=False
        ).select_related("post", "author")[:10],
    }
    return render(request, "dashboard/index.html", context)


@login_required
def post_create(request):
    if not _is_author(request.user):
        return render(request, "dashboard/not_an_author.html", status=403)
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_tags(post)
            messages.success(
                request,
                "Post published." if post.is_published else "Draft saved.",
            )
            return redirect(post.get_absolute_url() if post.is_published else "blog:dashboard")
    else:
        form = PostForm()
    return render(
        request,
        "dashboard/post_form.html",
        {"form": form, "heading": "Write a post", "submit_label": "Save"},
    )


@login_required
def post_edit(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if not _viewer_can_edit(request.user, post):
        return render(request, "dashboard/not_an_author.html", status=403)
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()
            messages.success(request, "Changes saved.")
            return redirect(post.get_absolute_url() if post.is_published else "blog:dashboard")
    else:
        form = PostForm(instance=post)
    return render(
        request,
        "dashboard/post_form.html",
        {"form": form, "post": post, "heading": "Edit post", "submit_label": "Save changes"},
    )


@login_required
@require_POST
def post_delete(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if not _viewer_can_edit(request.user, post):
        return HttpResponseBadRequest("Not your post.")
    post.delete()
    messages.success(request, "Post deleted.")
    return redirect("blog:dashboard")


@login_required
@require_POST
def markdown_preview(request):
    """Render Markdown for the editor's live preview pane."""
    return JsonResponse({"html": render_markdown(request.POST.get("content", ""))})


@login_required
@require_POST
def comment_moderate(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=pk)
    if comment.post.author_id != request.user.id and not request.user.is_staff:
        return HttpResponseBadRequest("Not your post.")
    if request.POST.get("action") == "approve":
        comment.is_approved = True
        comment.save(update_fields=["is_approved"])
        messages.success(request, "Comment approved.")
    else:
        comment.delete()
        messages.success(request, "Comment removed.")
    return redirect("blog:dashboard")


# --------------------------------------------------------------------------- #
# Static pages
# --------------------------------------------------------------------------- #


def about(request):
    authors = (
        User.objects.select_related("profile")
        .annotate(
            published=Count(
                "posts",
                filter=Q(posts__status=Post.Status.PUBLISHED, posts__published_at__lte=timezone.now()),
            )
        )
        .filter(published__gt=0)
        .order_by("-published")
    )
    return render(request, "blog/about.html", {"authors": authors})


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            message = form.save()
            mail_admins(
                subject=f"[{settings.SITE_NAME}] {message.subject}",
                message=f"From: {message.name} <{message.email}>\n\n{message.message}",
                fail_silently=True,
            )
            messages.success(request, "Thanks — your message is on its way.")
            return redirect("blog:contact")
    else:
        form = ContactForm()
    return render(request, "blog/contact.html", {"form": form})


@require_POST
def subscribe(request):
    form = SubscribeForm(request.POST)
    if form.is_valid():
        Subscriber.objects.get_or_create(email=form.cleaned_data["email"])
        messages.success(request, "You are on the list. New posts will land in your inbox.")
    else:
        messages.error(request, "That email address did not look right.")

    # `next` arrives in a form field, so it has to be vetted before redirecting.
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = reverse("blog:home")
    return redirect(target)


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request):
    """Rendered without context processors: a 500 can mean the database is down."""
    return HttpResponse(render_to_string("500.html"), status=500)
