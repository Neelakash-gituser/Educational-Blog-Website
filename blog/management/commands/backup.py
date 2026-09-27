"""Write a portable snapshot of the site's content.

    python manage.py backup

Produces backups/insight-<timestamp>.json — every post, comment, topic, tag,
account and contact message, in Django's own fixture format.  Restore it into
an empty database with:

    python manage.py loaddata backups/insight-<timestamp>.json

Worth running before an upgrade, and worth downloading now and then if the
site lives on SQLite.  Uploaded images are files, not database rows, so copy
the media/ directory alongside it.
"""

from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

# Content types and permissions are recreated by migrate, and stale rows in
# them break loaddata; sessions are worthless in a backup.
EXCLUDED = ["contenttypes", "auth.permission", "sessions", "admin.logentry"]


class Command(BaseCommand):
    help = "Write a JSON snapshot of all site content to backups/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=None,
            help="Write to this path instead of backups/insight-<timestamp>.json.",
        )
        parser.add_argument(
            "--keep",
            type=int,
            default=10,
            help="How many previous backups to keep (default 10, 0 keeps all).",
        )

    def handle(self, *args, **options):
        if options["output"]:
            target = Path(options["output"])
        else:
            stamp = datetime.now().strftime("%Y%m%d-%H%M")
            target = Path(settings.BASE_DIR) / "backups" / f"insight-{stamp}.json"
        target.parent.mkdir(parents=True, exist_ok=True)

        with target.open("w", encoding="utf-8") as handle:
            call_command(
                "dumpdata",
                *[f"--exclude={label}" for label in EXCLUDED],
                natural_foreign=True,
                natural_primary=True,
                indent=2,
                stdout=handle,
            )

        size_kb = target.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(f"Wrote {target} ({size_kb:.0f} KB)"))

        if options["keep"]:
            self._prune(target.parent, options["keep"])

        self.stdout.write(
            "Uploaded images live in media/ — copy that directory too for a full backup."
        )

    def _prune(self, directory, keep):
        backups = sorted(directory.glob("insight-*.json"), reverse=True)
        for stale in backups[keep:]:
            stale.unlink()
            self.stdout.write(f"Removed old backup {stale.name}")
