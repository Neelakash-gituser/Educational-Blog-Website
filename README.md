# Insight — an educational blog built with Django

A complete, production-ready blog for long-form technical writing: Markdown posts with
syntax-highlighted code and LaTeX maths, threaded comments, topics and tags, an author
dashboard with live preview, and a free-tier deployment path.

It replaces the original *Educational Blog Website* project and can import that project's
content (see [Importing the old site](#importing-the-old-site)).

---

## What it does

**Reading**

- Home page with a featured article, latest posts, topic cards, most-read list and tag cloud
- Article pages with a sticky table of contents, reading-progress bar, reading time, view
  count, related posts and an author card
- Topic pages, tag pages and author pages, each with search and four sort orders
  (newest, most read, most discussed, most liked)
- Full-text-ish search across titles, bodies, tags, topics and authors
- Light and dark themes, chosen by the reader and remembered; responsive down to 360px
- RSS feed, `sitemap.xml`, Open Graph / Twitter cards and JSON-LD per article

**Writing**

- Markdown editor in the browser with live preview, a formatting toolbar, word count and
  a cheat sheet — no admin access needed
- Fenced code blocks with Pygments highlighting, a language label and a copy button, in
  both themes
- LaTeX maths (`\(inline\)` and `$$display$$`) rendered by MathJax
- Tables, footnotes, admonitions/callouts, task lists and auto-linked URLs
- Drafts that only their author can see, cover images, excerpts (auto-generated if blank),
  featured flag, per-post comment switch
- Tags typed as free text, topics managed in the admin

**Discussion**

- Comments with one level of threaded replies, likes, edit and delete
- Markdown in comments — including code blocks — with a stricter allowlist than posts
- Optional moderation queue (`COMMENT_MODERATION=True`), surfaced in the dashboard
- Bookmarks (a per-reader reading list), post likes, and share links for X, LinkedIn,
  Reddit, Hacker News and email

**Safety and operations**

- All rendered Markdown is sanitised with bleach: no scripts, inline styles, iframes or
  `javascript:` URLs, from posts or comments
- Contact form with a honeypot, newsletter signups, admin actions for bulk publishing
  and comment approval
- 98 tests covering models, the Markdown pipeline, permissions and every page
- Production settings driven entirely by environment variables; HSTS, secure cookies and
  SSL redirect switch on automatically when `DEBUG=False`

---

## Quickstart

Requires Python 3.10+.

```bash
git clone https://github.com/Neelakash-gituser/Educational-Blog-Website.git
cd Educational-Blog-Website

python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt                       # add -r requirements-extras.txt for Postgres/Cloudinary

cp .env.example .env                                  # then edit SECRET_KEY at least

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo                            # topics + 5 example articles
python manage.py runserver
```

Open <http://127.0.0.1:8000>. The admin is at `/admin/`, the editor at `/dashboard/new/`.

`seed_demo` is idempotent — re-running it only adds what is missing, and `--flush` clears
the demo content first.

### Who can write

Reading, commenting and bookmarking are open to any signed-up account. Publishing needs
writer access, which is one checkbox:

- **Admin →  Profiles → *user* → Can write**, or
- make them staff/superuser, or
- `python manage.py shell -c "from django.contrib.auth.models import User; u=User.objects.get(username='alice'); u.profile.can_write=True; u.profile.save()"`

### Topics

Topics (categories) are created in the admin: name, emoji icon, accent colour, tagline and
sort position. The accent colour drives that topic's badges and cards across the site.

---

## Writing a post

Everything is Markdown. The formatting that matters:

````markdown
## A section heading          ← headings become the table of contents

Prose with **bold**, *italic*, `inline code` and [links](https://example.com).

```python
def f(x):
    return x * 2
```

> A pull quote.

| Column | Column |
| ------ | ------ |
| 1      | 2      |

!!! note "Optional title"
    An indented callout box.

- [x] task lists
- footnotes[^1]

Inline maths \(e^{i\pi} = -1\) and display maths:

$$ \int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2} $$

[^1]: Like this.
````

Post bodies are rendered to HTML **once, on save** (`Post.content_html`), so serving an
article is a single database read.

---

## Project layout

```
config/             settings, root URLs, WSGI/ASGI
blog/               posts, comments, topics, tags, contact, subscribers
  markdown_utils.py the Markdown → sanitised HTML pipeline
  views.py          reading, reader actions, dashboard
  management/commands/
    seed_demo.py        demo topics + articles
    import_legacy.py    import the original SQLite database
    make_code_css.py    regenerate the Pygments stylesheet
    backup.py           snapshot all content to backups/
  tests/            98 tests
accounts/           profiles, signup/login, settings
templates/          base + partials + page templates
static/css/main.css design system (tokens → primitives → components)
static/css/code.css generated: code chrome + Pygments tokens, both themes
static/js/main.js   progressive enhancement only; the site works without JS
legacy/             the original database, kept for the importer
deploy/             PythonAnywhere setup script and WSGI template
```

### Changing the look

`static/css/main.css` starts with a token block — colours, type scale, spacing, radii — for
light theme, then re-declares only the colour tokens for dark. Editing `--accent` and the
two font variables is usually enough to rebrand the whole site.

Code colours come from Pygments. To change the syntax theme, edit `LIGHT_STYLE` /
`DARK_STYLE` in `blog/management/commands/make_code_css.py` and run:

```bash
python manage.py make_code_css
```

---

## Configuration

All settings are read from the environment (or a local `.env`). See `.env.example`.

| Variable | Default | What it does |
| --- | --- | --- |
| `SECRET_KEY` | dev placeholder | **Set this in production.** |
| `DEBUG` | `True` | `False` turns on HSTS, secure cookies and SSL redirect |
| `ALLOWED_HOSTS` | localhost | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | — | Comma-separated; `https://` added if omitted |
| `DATABASE_URL` | local SQLite | Any `dj-database-url` URL (Postgres in production) |
| `DATABASE_SSL_REQUIRE` | `False` | Set `True` for most hosted Postgres |
| `SITE_NAME` / `SITE_TAGLINE` / `SITE_DESCRIPTION` | "Insight" … | Site identity and meta tags |
| `COMMENT_MODERATION` | `False` | `True` holds every comment for approval |
| `PAGINATE_BY` | `9` | Posts per page in listings |
| `TIME_ZONE` | `UTC` | Display timezone |
| `CLOUDINARY_URL` | — | If set, uploads go to Cloudinary instead of local disk |
| `SERVE_MEDIA` | on unless Cloudinary is set | Lets Django serve `/media/` in production |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | console backend | SMTP for contact-form notifications |

---

## Deploying free

Full click-by-click instructions, including the free Postgres and image-hosting steps, are
in **[DEPLOY.md](DEPLOY.md)**. In short:

| Host | Free tier | Files used |
| --- | --- | --- |
| **PythonAnywhere** (recommended) | One web app that never sleeps, SQLite, no card needed | `deploy/pythonanywhere_setup.sh`, `deploy/pythonanywhere_wsgi.py` |
| **Render** | Web service + Postgres, but it sleeps when idle and the free database expires after 30 days | `render.yaml`, `build.sh` |
| **Fly.io** | Small always-on VM, card required | `Dockerfile`, `fly.toml` |
| **Railway / Koyeb / Cloud Run** | Varies | `Dockerfile` or `Procfile` |

On PythonAnywhere the whole deploy is one script:

```bash
git clone https://github.com/Neelakash-gituser/Educational-Blog-Website.git
cd Educational-Blog-Website
bash deploy/pythonanywhere_setup.sh     # venv, deps, .env with a fresh key, migrate, static
python manage.py createsuperuser
```

then point the Web tab at the project and reload — [DEPLOY.md](DEPLOY.md) has the exact
field values.

Static files are served by WhiteNoise, so no separate CDN or nginx is needed. Container
hosts have ephemeral disks, so set `CLOUDINARY_URL` there if you upload cover images —
on PythonAnywhere the disk is real and uploads simply stay put.

---

## Importing the old site

The original project's database is kept at `legacy/db.sqlite3`. To bring its content over:

```bash
python manage.py import_legacy                     # reads legacy/db.sqlite3
python manage.py import_legacy --db /path/to/db.sqlite3 --author alice
```

The mapping is: `Subject → Category`, `Detail → published Post`, `Article → draft Post`
(so you can review reader submissions before publishing), `Connect → ContactMessage`.
Posts are attributed to `--author`, or to the first superuser. Re-running it skips anything
already imported.

---

## Backups

```bash
python manage.py backup
```

Writes `backups/insight-<timestamp>.json` — every post, comment, topic, tag and account —
and keeps the ten most recent. Restore with `python manage.py loaddata <file>` into a
migrated database. Uploaded images are files rather than rows, so copy `media/` too.
Worth doing regularly if the site runs on SQLite.

---

## Tests

```bash
python manage.py test               # 98 tests
python manage.py test blog.tests.test_markdown -v 2
```

They cover slug generation, publishing rules, reading-time and excerpt derivation, the
Markdown pipeline (highlighting, maths, and sanitising against XSS), comment threading and
moderation, permissions on every write endpoint, and a smoke test of every page — including
that a post slugged `about` cannot shadow the About page.

---

## Licence

MIT. Written by Neelakash Chatterjee.
