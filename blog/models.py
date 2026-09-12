"""Data model for the blog.

Post bodies are written in Markdown and rendered to HTML on save, so serving a
post is a single database read with no Markdown work per request.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .markdown_utils import (
    reading_time,
    render_comment,
    render_markdown,
    render_toc,
    strip_markdown,
    word_count,
)


def unique_slugify(instance, value, field_name="slug", max_length=200):
    """Slugify ``value``, appending -2, -3 … until the slug is free."""
    base = slugify(value)[:max_length] or "untitled"
    slug = base
    model = instance.__class__
    counter = 2
    while (
        model._default_manager.filter(**{field_name: slug})
        .exclude(pk=instance.pk)
        .exists()
    ):
        suffix = f"-{counter}"
        slug = f"{base[: max_length - len(suffix)]}{suffix}"
        counter += 1
    return slug


class Category(models.Model):
    """A broad topic, e.g. "Computer Science" or "Physics"."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    tagline = models.CharField(
        max_length=160, blank=True, help_text="One line shown on the topic page."
    )
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=8, default="✳", help_text="A single emoji used as the topic badge."
    )
    color = models.CharField(
        max_length=7,
        default="#6366f1",
        help_text="Hex accent colour, e.g. #6366f1.",
    )
    position = models.PositiveIntegerField(default=0, help_text="Lower sorts first.")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["position", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:category", args=[self.slug])

    @property
    def published_count(self):
        return self.posts.published().count()


class Tag(models.Model):
    """A fine-grained label, e.g. "recursion" or "thermodynamics"."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:tag", args=[self.slug])


class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Post.Status.PUBLISHED, published_at__lte=timezone.now())

    def drafts(self):
        return self.exclude(status=Post.Status.PUBLISHED)

    def with_related(self):
        return self.select_related("author", "author__profile", "category").prefetch_related("tags")

    def with_counts(self):
        return self.annotate(
            comment_total=Count(
                "comments", filter=Q(comments__is_approved=True), distinct=True
            ),
            like_total=Count("likes", distinct=True),
        )

    def search(self, query):
        if not query:
            return self
        return self.filter(
            Q(title__icontains=query)
            | Q(excerpt__icontains=query)
            | Q(content__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(category__name__icontains=query)
            | Q(author__username__icontains=query)
            | Q(author__first_name__icontains=query)
            | Q(author__last_name__icontains=query)
        ).distinct()


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=250, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")

    excerpt = models.TextField(
        max_length=400,
        blank=True,
        help_text="Short teaser shown in listings. Generated from the body if left blank.",
    )
    content = models.TextField(help_text="Markdown. Fenced code blocks are highlighted.")
    content_html = models.TextField(blank=True, editable=False)
    toc_html = models.TextField(blank=True, editable=False)

    cover_image = models.ImageField(upload_to="covers/%Y/%m", blank=True)
    cover_caption = models.CharField(max_length=200, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    is_featured = models.BooleanField(
        default=False, help_text="Featured posts headline the home page."
    )
    allow_comments = models.BooleanField(default=True)

    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    view_count = models.PositiveIntegerField(default=0, editable=False)
    read_minutes = models.PositiveIntegerField(default=1, editable=False)
    words = models.PositiveIntegerField(default=0, editable=False)

    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="liked_posts"
    )
    bookmarks = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="bookmarked_posts"
    )

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["-published_at"]),
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        self.content_html = render_markdown(self.content)
        self.toc_html = render_toc(self.content)
        self.words = word_count(self.content)
        self.read_minutes = reading_time(self.content)
        if not self.excerpt:
            self.excerpt = strip_markdown(self.content, limit=220)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:post_detail", args=[self.slug])

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED and bool(
            self.published_at and self.published_at <= timezone.now()
        )

    @property
    def display_date(self):
        return self.published_at or self.created_at

    @property
    def approved_comments(self):
        return self.comments.filter(is_approved=True, parent__isnull=True)

    def comment_count(self):
        return self.comments.filter(is_approved=True).count()

    def related_posts(self, limit=3):
        """Posts sharing tags first, then the same category."""
        qs = (
            Post.objects.published()
            .exclude(pk=self.pk)
            .with_related()
            .filter(Q(tags__in=self.tags.all()) | Q(category=self.category))
            .annotate(shared=Count("tags", filter=Q(tags__in=self.tags.all())))
            .order_by("-shared", "-published_at")
            .distinct()
        )
        return qs[:limit]

    def register_view(self):
        """Increment the view counter without touching ``updated_at``."""
        Post.objects.filter(pk=self.pk).update(view_count=models.F("view_count") + 1)


class Comment(models.Model):
    """A reader comment. One level of threading: a reply points at a root comment."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    body = models.TextField(max_length=5000, help_text="Markdown, including code blocks.")
    body_html = models.TextField(blank=True, editable=False)
    is_approved = models.BooleanField(default=True)
    is_edited = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="liked_comments"
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["post", "created_at"])]

    def __str__(self):
        return f"{self.author} on {self.post}"

    def save(self, *args, **kwargs):
        # Only one level of nesting: a reply to a reply attaches to its root.
        if self.parent and self.parent.parent_id:
            self.parent = self.parent.parent
        self.body_html = render_comment(self.body)
        super().save(*args, **kwargs)

    @property
    def visible_replies(self):
        return self.replies.filter(is_approved=True).select_related(
            "author", "author__profile"
        )


class ContactMessage(models.Model):
    """A message from the contact form."""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}> — {self.subject}"


class Subscriber(models.Model):
    """Email address collected by the newsletter form."""

    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
