# Deploying

The blog is a normal Django app: any host that runs Python and can serve a WSGI
application will do. **PythonAnywhere** is documented first because it is the option
that stays free without a payment card, without sleeping, and without a database that
expires. The other hosts are covered further down.

---

## PythonAnywhere (free, no card)

### What the free tier gives you, honestly

| | |
| --- | --- |
| Address | `https://<username>.pythonanywhere.com` (HTTPS included) |
| Web app | One, and it does **not** sleep between visits |
| Database | SQLite — MySQL moved to the paid tier for new free accounts in January 2026 |
| Python | 3.11, 3.12 or 3.13 on accounts created after March 2025, with no preinstalled packages, so you make a virtualenv |
| Renewal | You click a button to keep the web app alive; an **unused** app now expires after about a month, so a visit from you every few weeks is enough |
| Support | Community forums only on free accounts since January 2026 |
| Outbound internet | Restricted, so the contact form cannot send email. Messages are still saved and readable in the admin — nothing is lost, you just read them there |

SQLite on a single always-on worker is genuinely fine for a blog: the app switches it into
WAL mode automatically, so readers never block on you publishing. Take backups (see
[Backups](#backups)), because the data lives on that one disk.

### Steps

**1. Sign up** at [pythonanywhere.com](https://www.pythonanywhere.com) and choose the free
"Beginner" account.

**2. Open a Bash console** (Consoles → Bash) and run:

```bash
git clone https://github.com/Neelakash-gituser/Educational-Blog-Website.git
cd Educational-Blog-Website
git checkout claude/django-blog-redesign-ezgs90     # skip if you merged it into master
bash deploy/pythonanywhere_setup.sh
```

That script makes a virtualenv, installs `requirements.txt` (core only — it deliberately
skips the Postgres and Cloudinary packages you do not need here), writes a `.env` with a
freshly generated `SECRET_KEY`, runs migrations and collects static files. It prints the
exact paths you need for the next step, so keep the console open.

**3. Create your login, and optionally some content:**

```bash
python manage.py createsuperuser
python manage.py seed_demo        # demo topics + five example articles
python manage.py import_legacy    # content from the original site
```

**4. Configure the web app.** Go to the **Web** tab → **Add a new web app** →
**Manual configuration** (*not* the "Django" option — that scaffolds a new project over
yours) → the same Python version you used above. Then fill in:

| Field | Value |
| --- | --- |
| Source code | `/home/<username>/Educational-Blog-Website` |
| Working directory | `/home/<username>/Educational-Blog-Website` |
| Virtualenv | `/home/<username>/.virtualenvs/insight` |

**5. Set the WSGI file.** Click the WSGI configuration file link on that page, delete
everything in it, and paste the contents of [`deploy/pythonanywhere_wsgi.py`](deploy/pythonanywhere_wsgi.py),
changing `USERNAME` to your username. Save.

**6. Map the static files** in the **Static files** section of the Web tab:

| URL | Directory |
| --- | --- |
| `/static/` | `/home/<username>/Educational-Blog-Website/staticfiles` |
| `/media/` | `/home/<username>/Educational-Blog-Website/media` |

**7. Tick "Force HTTPS"**, then press the big green **Reload** button.

Your blog is at `https://<username>.pythonanywhere.com`. The admin is at `/admin/`, and
you write at `/dashboard/new/`.

### Publishing changes later

Anything you write through the site's own editor is live immediately — no deploy needed.
You only repeat this when the *code* changes:

```bash
cd ~/Educational-Blog-Website
source ~/.virtualenvs/insight/bin/activate
git pull
pip install -r requirements.txt      # only if requirements.txt changed
python manage.py migrate
python manage.py collectstatic --no-input
```

Then hit **Reload** on the Web tab.

### A custom domain

Custom domains need a paid account on PythonAnywhere. Until then the
`<username>.pythonanywhere.com` address is permanent. If you do add one later, update
`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `SITE_URL` in `.env` and reload.

### If something goes wrong

The **Web** tab has an *Error log* and a *Server log*; the traceback you need is almost
always at the bottom of the error log. Two common ones:

- **"DisallowedHost"** — `ALLOWED_HOSTS` in `.env` does not list your address.
- **Unstyled page** — the `/static/` mapping is missing or points at `static/` instead of
  `staticfiles/`. Re-run `collectstatic` and check the path.

---

## Backups

The whole point of SQLite is that your data is one file. Keep copies of it:

```bash
python manage.py backup            # writes backups/insight-<timestamp>.json
```

That snapshot holds every post, comment, topic, tag and account, and keeps the ten most
recent files. Download it from the **Files** tab now and then. Uploaded images are files
rather than rows, so grab the `media/` directory too.

Restoring into an empty database:

```bash
python manage.py migrate
python manage.py loaddata backups/insight-<timestamp>.json
```

---

## Other hosts

### Render

`render.yaml` and `build.sh` deploy the app with Postgres as a blueprint (**New →
Blueprint**, pick the repo, **Apply**). Note two free-tier limits before relying on it:
the web service **sleeps after 15 minutes idle**, and free Postgres databases **expire 30
days after creation**, with a 14-day grace period before deletion. Good for showing
someone; not a permanent home unless you pay.

### Fly.io

`Dockerfile` and `fly.toml` are ready. Needs a card on file even inside the free
allowance.

```bash
fly launch --no-deploy
fly postgres create --name insight-db && fly postgres attach insight-db
fly secrets set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')" \
                DEBUG=False ALLOWED_HOSTS="insight-blog.fly.dev" DATABASE_SSL_REQUIRE=True
fly deploy
fly ssh console -C "python manage.py createsuperuser"
```

### Railway, Koyeb, Cloud Run, Heroku-likes

All accept the `Dockerfile` or the `Procfile`. Set `SECRET_KEY`, `DEBUG=False`,
`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL` and `DATABASE_SSL_REQUIRE=True`,
and install `requirements-extras.txt` so the Postgres driver is present.
[Neon](https://neon.tech) and [Supabase](https://supabase.com) both hand out a free
Postgres connection string if the host does not include a database.

### Uploaded images on hosts with an ephemeral disk

Render, Fly and most container hosts wipe the filesystem on every deploy. Set
`CLOUDINARY_URL` (free tier at [cloudinary.com](https://cloudinary.com)) and uploads go
there instead — the app detects it and switches storage on its own. PythonAnywhere has a
real disk, so this does not apply there.

---

## Checklist before going live

- [ ] `SECRET_KEY` is long, random and not in git (the setup script generates one)
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` lists your real hostname
- [ ] `CSRF_TRUSTED_ORIGINS` lists `https://your-hostname`
- [ ] Static files are mapped (or `collectstatic` has run on hosts using WhiteNoise)
- [ ] A superuser exists and `/admin/` loads
- [ ] `python manage.py check --deploy` shows nothing you have not consciously accepted
- [ ] You have run `python manage.py backup` once and know where the file lands
