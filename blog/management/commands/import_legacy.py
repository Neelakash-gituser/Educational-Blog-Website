"""Import content from the original csandphysicsblog SQLite database.

The old schema stored topics in ``csandphysicsblog_subject``, articles in
``csandphysicsblog_detail`` plus ``csandphysicsblog_article``, and contact
messages in ``Connect``.  This command reads that file directly — no old Django
app or models required — and maps it onto the new schema:

    Subject  -> Category
    Detail   -> Post   (published, attributed to --author)
    Article  -> Post   (draft, so you can review before publishing)
    Connect  -> ContactMessage

Usage:

    python manage.py import_legacy               # reads legacy/db.sqlite3
    python manage.py import_legacy --db path.sqlite3 --author neelakash
"""

import sqlite3
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from blog.models import Category, ContactMessage, Post

DEFAULT_DB = "legacy/db.sqlite3"


def table_exists(connection, name):
    cursor = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cursor.fetchone() is not None


class Command(BaseCommand):
    help = "Import topics, posts and messages from the original SQLite database."

    def add_arguments(self, parser):
        parser.add_argument("--db", default=DEFAULT_DB, help=f"Path to the old database (default {DEFAULT_DB}).")
        parser.add_argument("--author", default=None, help="Username to attribute imported posts to.")
        parser.add_argument(
            "--publish-articles",
            action="store_true",
            help="Publish imported reader articles instead of importing them as drafts.",
        )

    def handle(self, *args, **options):
        path = Path(options["db"])
        if not path.is_absolute():
            path = Path(settings.BASE_DIR) / path
        if not path.exists():
            raise CommandError(f"No database at {path}")

        author = self._resolve_author(options["author"])
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row

        created = {"categories": 0, "posts": 0, "messages": 0}

        # Subject -> Category
        if table_exists(connection, "csandphysicsblog_subject"):
            for row in connection.execute("SELECT * FROM csandphysicsblog_subject"):
                name = (row["Topic"] or "").strip()
                if not name:
                    continue
                _, made = Category.objects.get_or_create(
                    slug=slugify(name),
                    defaults={"name": name, "tagline": f"Everything filed under {name}."},
                )
                created["categories"] += int(made)

        # Detail -> published Post
        if table_exists(connection, "csandphysicsblog_detail"):
            for row in connection.execute("SELECT * FROM csandphysicsblog_detail"):
                title = (row["Sub_Topic"] or "").strip() or "Untitled"
                if Post.objects.filter(slug=slugify(title)).exists():
                    self.stdout.write(f"  = skipped (exists): {title}")
                    continue
                category = self._category_for_subject(connection, row["Heading_id"])
                published = self._parse_date(row["Date_added"])
                body = (row["Content"] or "").strip()
                byline = (row["Added_by"] or "").strip()
                if byline:
                    body = f"{body}\n\n---\n\n*Originally credited to: {byline}*"
                post = Post(
                    title=title,
                    author=author,
                    category=category,
                    content=body,
                    status=Post.Status.PUBLISHED,
                    published_at=published,
                )
                post.save()
                created["posts"] += 1
                self.stdout.write(f"  + post {post.title}")

        # Article -> draft Post
        if table_exists(connection, "csandphysicsblog_article"):
            status = (
                Post.Status.PUBLISHED if options["publish_articles"] else Post.Status.DRAFT
            )
            for row in connection.execute("SELECT * FROM csandphysicsblog_article"):
                title = (row["Sub_Topic"] or "").strip() or "Untitled article"
                if Post.objects.filter(slug=slugify(title)).exists():
                    self.stdout.write(f"  = skipped (exists): {title}")
                    continue
                topic = (row["Topic"] or "").strip()
                category = None
                if topic:
                    category, _ = Category.objects.get_or_create(
                        slug=slugify(topic), defaults={"name": topic}
                    )
                body = (row["Matter"] or "").strip()
                contributor = (row["Author"] or "").strip()
                if contributor:
                    body = f"{body}\n\n---\n\n*Contributed by: {contributor}*"
                post = Post(
                    title=title,
                    subtitle=f"Reader contribution{f' by {contributor}' if contributor else ''}",
                    author=author,
                    category=category,
                    content=body,
                    status=status,
                    published_at=timezone.now() if status == Post.Status.PUBLISHED else None,
                )
                post.save()
                created["posts"] += 1
                self.stdout.write(f"  + {'post' if status == Post.Status.PUBLISHED else 'draft'} {post.title}")

        # Connect -> ContactMessage
        if table_exists(connection, "Connect"):
            for row in connection.execute("SELECT * FROM Connect"):
                email = (row["Email"] or "").strip()
                if not email:
                    continue
                _, made = ContactMessage.objects.get_or_create(
                    email=email,
                    subject=(row["Topic"] or "Imported message")[:150],
                    defaults={
                        "name": (row["Name"] or "Unknown")[:100],
                        "message": row["Message"] or "",
                    },
                )
                created["messages"] += int(made)

        connection.close()
        self.stdout.write(
            self.style.SUCCESS(
                "Imported {categories} topic(s), {posts} post(s), {messages} message(s).".format(**created)
            )
        )

    def _category_for_subject(self, connection, subject_id):
        if not subject_id or not table_exists(connection, "csandphysicsblog_subject"):
            return None
        row = connection.execute(
            "SELECT Topic FROM csandphysicsblog_subject WHERE id = ?", (subject_id,)
        ).fetchone()
        if row is None or not (row["Topic"] or "").strip():
            return None
        name = row["Topic"].strip()
        category, _ = Category.objects.get_or_create(slug=slugify(name), defaults={"name": name})
        return category

    @staticmethod
    def _parse_date(value):
        if not value:
            return timezone.now()
        try:
            from datetime import datetime

            naive = datetime.strptime(str(value)[:10], "%Y-%m-%d")
            return timezone.make_aware(naive, timezone.get_default_timezone())
        except (ValueError, TypeError):
            return timezone.now()

    def _resolve_author(self, username):
        if username:
            user = User.objects.filter(username=username).first()
            if user is None:
                raise CommandError(f"No user named {username!r}.")
            return user
        user = User.objects.filter(is_superuser=True).order_by("pk").first()
        if user is None:
            raise CommandError(
                "No superuser to attribute posts to. Run `python manage.py createsuperuser` "
                "first, or pass --author."
            )
        return user
