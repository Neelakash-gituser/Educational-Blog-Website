"""Small helpers so each test reads as one obvious arrangement."""

from django.contrib.auth.models import User

from blog.models import Category, Post


def make_user(username="reader", *, writer=False, staff=False, password="test-pass-123"):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password=password)
    user.is_staff = staff
    user.save()
    profile = user.profile
    profile.can_write = writer
    profile.save()
    return user


def make_category(name="Computer Science", **kwargs):
    return Category.objects.create(name=name, **kwargs)


def make_post(author, *, title="A post about things", published=True, **kwargs):
    kwargs.setdefault("content", "Some **body** text that is long enough to matter.")
    return Post.objects.create(
        title=title,
        author=author,
        status=Post.Status.PUBLISHED if published else Post.Status.DRAFT,
        **kwargs,
    )
