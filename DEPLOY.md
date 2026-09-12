# Deploying for free

Four options, cheapest effort first. Every one of them runs the same code — the only
difference is which of the config files in this repo the platform reads.

Whichever you pick, you need three things: a **secret key**, a **database**, and somewhere
for **uploaded images** to live.

---

## Option 1 — Render (recommended)

Free web service plus a free Postgres database, configured by `render.yaml` and `build.sh`.
The free web service sleeps after 15 minutes of inactivity and takes ~30 seconds to wake.

### Steps

1. Push this repository to GitHub.
2. Sign up at [render.com](https://render.com) and connect your GitHub account.
3. **New → Blueprint**, pick this repository. Render reads `render.yaml` and proposes a web
   service plus a Postgres database. Click **Apply**.
4. Wait for the first build. `build.sh` installs dependencies, runs `collectstatic` and
   applies migrations.
5. Create your login. In the service's **Shell** tab:

   ```bash
   python manage.py createsuperuser
   python manage.py seed_demo        # optional: demo topics and articles
   ```

6. Open the URL Render assigned you (`https://insight-blog.onrender.com` or similar).

`render.yaml` already sets `DEBUG=False`, generates `SECRET_KEY`, wires `DATABASE_URL` to
the free database and sets `DATABASE_SSL_REQUIRE=True`. `RENDER_EXTERNAL_HOSTNAME` is
provided by Render and picked up automatically for `ALLOWED_HOSTS` and
`CSRF_TRUSTED_ORIGINS`, so there is nothing to fill in by hand.

### Doing it without the blueprint

If you would rather click through it: **New → Web Service**, connect the repo, then set

- Build command: `./build.sh`
- Start command: `gunicorn config.wsgi:application`
- Environment: `SECRET_KEY` (any 50 random characters), `DEBUG=False`,
  `DATABASE_URL` (from a separately created Postgres instance),
  `DATABASE_SSL_REQUIRE=True`

### Custom domain

Add it under **Settings → Custom Domains**, then add the hostname to `ALLOWED_HOSTS` and
`CSRF_TRUSTED_ORIGINS`, and set `SITE_URL=https://yourdomain.com`.

---

## Option 2 — Fly.io

A small always-on VM, no sleeping, using `Dockerfile` and `fly.toml`.

```bash
curl -L https://fly.io/install.sh | sh
fly auth signup

fly launch --no-deploy                      # accept the app name or change it in fly.toml
fly postgres create --name insight-db       # then attach it:
fly postgres attach insight-db              # sets DATABASE_URL for you

fly secrets set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')" \
                DEBUG=False \
                DATABASE_SSL_REQUIRE=True \
                ALLOWED_HOSTS="insight-blog.fly.dev"

fly deploy
fly ssh console -C "python manage.py createsuperuser"
```

Migrations run on boot (see the `CMD` in `Dockerfile`).

---

## Option 3 — Railway, Koyeb, Cloud Run, Heroku-likes

All of these accept either the `Dockerfile` or the `Procfile`:

```
release: python manage.py migrate --noinput
web: gunicorn config.wsgi:application --log-file -
```

Set these environment variables:

```
SECRET_KEY=<50 random characters>
DEBUG=False
ALLOWED_HOSTS=<your-app-hostname>
CSRF_TRUSTED_ORIGINS=https://<your-app-hostname>
DATABASE_URL=<postgres url>
DATABASE_SSL_REQUIRE=True
```

For a free database with any of them, [Neon](https://neon.tech) and
[Supabase](https://supabase.com) both give you a Postgres instance and a connection string
to paste into `DATABASE_URL`.

---

## Option 4 — PythonAnywhere

One always-on free web app, SQLite only, no sleeping. Good if you want the simplest thing
that stays awake.

1. Sign up, open a **Bash** console:

   ```bash
   git clone https://github.com/Neelakash-gituser/Educational-Blog-Website.git
   cd Educational-Blog-Website
   mkvirtualenv insight --python=/usr/bin/python3.11
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py collectstatic --no-input
   ```

2. **Web → Add a new web app → Manual configuration → Python 3.11**.
3. Set the virtualenv to `/home/<you>/.virtualenvs/insight`.
4. Edit the WSGI file to:

   ```python
   import os, sys
   path = "/home/<you>/Educational-Blog-Website"
   if path not in sys.path:
       sys.path.insert(0, path)
   os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
   os.environ["DEBUG"] = "False"
   os.environ["SECRET_KEY"] = "<50 random characters>"
   os.environ["ALLOWED_HOSTS"] = "<you>.pythonanywhere.com"
   os.environ["SECURE_SSL_REDIRECT"] = "False"   # PythonAnywhere terminates TLS itself
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

5. Under **Static files**, map `/static/` to
   `/home/<you>/Educational-Blog-Website/staticfiles` and `/media/` to
   `/home/<you>/Educational-Blog-Website/media`.
6. Reload the web app.

SQLite on a single always-on worker is genuinely fine for a blog. Back it up by
downloading `db.sqlite3` occasionally.

---

## Uploaded images on a free tier

Free hosts give you an **ephemeral filesystem**: anything uploaded through the editor
disappears on the next deploy or restart. Two ways round it:

**Cloudinary free tier (recommended).** Sign up at
[cloudinary.com](https://cloudinary.com), copy the `CLOUDINARY_URL` from your dashboard
(`cloudinary://key:secret@cloud-name`) and set it as an environment variable. The app
detects it and stores every upload there instead; nothing else changes.

**Skip uploads.** Posts look fine without cover images — each one falls back to its topic's
emoji on a coloured gradient. You can also paste image URLs straight into Markdown:
`![alt](https://…)`.

---

## After the first deploy

```bash
python manage.py createsuperuser     # your login
python manage.py seed_demo           # demo topics + articles (optional)
python manage.py import_legacy       # bring over the old site's content (optional)
```

Then, in the admin:

1. **Categories** — create your topics with icons and accent colours.
2. **Profiles** — tick *Can write* for anyone who should be able to publish.
3. **Users** — your own profile: display name, headline, bio, avatar, links.

Set `SITE_NAME`, `SITE_TAGLINE` and `SITE_DESCRIPTION` in the environment to brand the
site; they feed the header, footer and every meta tag.

---

## Checklist before going live

- [ ] `SECRET_KEY` set to something random and secret (never the repo default)
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` lists your real hostname
- [ ] `CSRF_TRUSTED_ORIGINS` lists `https://your-hostname`
- [ ] `DATABASE_URL` points at Postgres (not the bundled SQLite) on multi-worker hosts
- [ ] `CLOUDINARY_URL` set if you plan to upload images
- [ ] `python manage.py check --deploy` reports nothing you have not consciously accepted
- [ ] A superuser exists and you can reach `/admin/`
