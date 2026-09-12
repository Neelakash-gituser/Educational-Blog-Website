from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Comment, ContactMessage, Post, Subscriber, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("badge", "name", "slug", "position", "published_count")
    list_editable = ("position",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "tagline", "description")

    @admin.display(description="")
    def badge(self, obj):
        return format_html(
            '<span style="background:{};color:#fff;border-radius:6px;padding:2px 8px">{}</span>',
            obj.color,
            obj.icon,
        )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "post_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    @admin.display(description="posts")
    def post_count(self, obj):
        return obj.posts.count()


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "status", "published_at", "view_count", "comments_count")
    list_filter = ("status", "is_featured", "category", "author")
    search_fields = ("title", "subtitle", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("tags", "category")
    date_hierarchy = "published_at"
    readonly_fields = ("view_count", "read_minutes", "words", "created_at", "updated_at")
    actions = ("publish_selected", "unpublish_selected")
    fieldsets = (
        (None, {"fields": ("title", "subtitle", "slug", "author", "category", "tags")}),
        ("Body", {"fields": ("excerpt", "content")}),
        ("Cover", {"fields": ("cover_image", "cover_caption")}),
        ("Publishing", {"fields": ("status", "published_at", "is_featured", "allow_comments")}),
        ("Stats", {"fields": ("view_count", "read_minutes", "words", "created_at", "updated_at")}),
    )

    @admin.display(description="comments")
    def comments_count(self, obj):
        return obj.comments.count()

    @admin.action(description="Publish selected posts")
    def publish_selected(self, request, queryset):
        for post in queryset:
            post.status = Post.Status.PUBLISHED
            post.save()

    @admin.action(description="Move selected posts back to draft")
    def unpublish_selected(self, request, queryset):
        queryset.update(status=Post.Status.DRAFT)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "post", "short_body", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("body", "author__username", "post__title")
    actions = ("approve_selected",)

    @admin.display(description="comment")
    def short_body(self, obj):
        return obj.body[:70] + ("…" if len(obj.body) > 70 else "")

    @admin.action(description="Approve selected comments")
    def approve_selected(self, request, queryset):
        queryset.update(is_approved=True)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "created_at", "is_handled")
    list_filter = ("is_handled",)
    search_fields = ("name", "email", "subject", "message")


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at", "is_active")
    list_filter = ("is_active",)
    search_fields = ("email",)


admin.site.site_header = "Insight admin"
admin.site.site_title = "Insight admin"
admin.site.index_title = "Content"
