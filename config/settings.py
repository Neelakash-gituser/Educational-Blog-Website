"""
Django settings for the Insight blog project.

Everything that differs between local development and production is read from
environment variables so the same code can be deployed anywhere.  Copy
``.env.example`` to ``.env`` for local development.
"""

from pathlib import Path

import dj_database_url
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")

DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")

# Platforms such as Render expose the external hostname through an env var.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

if DEBUG and "*" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("*")

CSRF_TRUSTED_ORIGINS = [
    origin if "://" in origin else f"https://{origin}"
    for origin in env_list("CSRF_TRUSTED_ORIGINS")
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "blog",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "blog.context_processors.site_chrome",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=env_bool("DATABASE_SSL_REQUIRE", False),
    )
}

if "sqlite" in DATABASES["default"]["ENGINE"]:
    # SQLite is a real option for a blog on a single worker (PythonAnywhere,
    # a small VPS), but it needs different settings from a network database:
    # WAL so readers never block on the writer, a busy timeout instead of an
    # instant "database is locked", and no persistent connections.
    DATABASES["default"]["CONN_MAX_AGE"] = 0
    DATABASES["default"].setdefault("OPTIONS", {}).update(
        {
            "timeout": 20,
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        }
    )

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "blog:home"
LOGOUT_REDIRECT_URL = "blog:home"


# --------------------------------------------------------------------------- #
# I18N
# --------------------------------------------------------------------------- #

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True


# --------------------------------------------------------------------------- #
# Static & media
# --------------------------------------------------------------------------- #

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

# Free hosting tiers usually have an ephemeral filesystem, so uploaded images
# disappear on redeploy.  Setting CLOUDINARY_URL moves media to Cloudinary's
# free tier instead; everything else keeps working unchanged.
USE_CLOUDINARY = False
if os.environ.get("CLOUDINARY_URL"):
    try:
        import cloudinary_storage  # noqa: F401

        INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]
        STORAGES["default"] = {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"
        }
        USE_CLOUDINARY = True
    except ImportError:  # pragma: no cover - optional dependency
        pass

# With local storage there is no web server in front of MEDIA_ROOT on a
# single-container host, so Django serves uploads itself.  Fine for a blog's
# handful of cover images; switch it off if a CDN or Cloudinary handles them.
SERVE_MEDIA = env_bool("SERVE_MEDIA", not USE_CLOUDINARY)


# --------------------------------------------------------------------------- #
# Email (contact form notifications)
# --------------------------------------------------------------------------- #

if os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@example.com")


# --------------------------------------------------------------------------- #
# Security (production)
# --------------------------------------------------------------------------- #

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", 60 * 60 * 24 * 30))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"


# --------------------------------------------------------------------------- #
# Site chrome — surfaced to every template by blog.context_processors
# --------------------------------------------------------------------------- #

SITE_NAME = os.environ.get("SITE_NAME", "Insight")
SITE_TAGLINE = os.environ.get(
    "SITE_TAGLINE", "Deep dives on computer science, physics and everything in between."
)
SITE_DESCRIPTION = os.environ.get(
    "SITE_DESCRIPTION",
    "An educational blog about computer science, physics, mathematics and economics — "
    "written for curious people who want the details, not the summary.",
)
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000")

# Comments appear immediately unless you flip this on, in which case a staff
# member has to approve each one from the admin or the dashboard.
COMMENT_MODERATION = env_bool("COMMENT_MODERATION", False)
PAGINATE_BY = int(os.environ.get("PAGINATE_BY", 9))
