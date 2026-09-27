#!/usr/bin/env bash
# First-time setup on PythonAnywhere. Run it in a Bash console:
#
#   git clone https://github.com/Neelakash-gituser/Educational-Blog-Website.git
#   cd Educational-Blog-Website
#   bash deploy/pythonanywhere_setup.sh
#
# It creates the virtualenv, installs dependencies, writes a .env with a fresh
# secret key, sets up the database and collects static files. Re-running it is
# safe: an existing .env is never overwritten.
set -o errexit

PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
VENV_NAME="${VENV_NAME:-insight}"
VENV_PATH="$HOME/.virtualenvs/$VENV_NAME"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_DIR"

if [ ! -d "$VENV_PATH" ]; then
  echo "==> Creating virtualenv $VENV_NAME (Python $PYTHON_VERSION)"
  "python$PYTHON_VERSION" -m venv "$VENV_PATH"
fi

# shellcheck disable=SC1091
source "$VENV_PATH/bin/activate"

echo "==> Installing dependencies (core only — no Postgres or Cloudinary)"
pip install --upgrade pip --quiet
pip install -r requirements.txt

if [ ! -f .env ]; then
  echo "==> Writing .env"
  SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
  cat > .env <<ENVEOF
SECRET_KEY=$SECRET
DEBUG=False
ALLOWED_HOSTS=$USER.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://$USER.pythonanywhere.com
SITE_URL=https://$USER.pythonanywhere.com

# PythonAnywhere terminates TLS in front of the app and has its own
# "Force HTTPS" switch on the Web tab, so Django must not redirect as well.
SECURE_SSL_REDIRECT=False

SITE_NAME=Insight
SITE_TAGLINE=Deep dives on computer science, physics and everything in between.
TIME_ZONE=UTC

# Free accounts cannot reach an outside SMTP server, so contact-form emails
# stay off; the messages are still saved and readable in the admin.
ENVEOF
else
  echo "==> .env already exists, leaving it alone"
fi

echo "==> Applying migrations"
python manage.py migrate --no-input

echo "==> Collecting static files"
python manage.py collectstatic --no-input

cat <<DONE

Setup finished.

Next:
  1. python manage.py createsuperuser
  2. python manage.py seed_demo        (optional: demo topics and articles)
  3. python manage.py import_legacy    (optional: content from the old site)

Then on the Web tab:
  - Virtualenv:  $VENV_PATH
  - Source code: $PROJECT_DIR
  - WSGI file:   paste deploy/pythonanywhere_wsgi.py, set USERNAME = $USER
  - Static files:  /static/  ->  $PROJECT_DIR/staticfiles
                   /media/   ->  $PROJECT_DIR/media
  - Tick "Force HTTPS", then hit Reload.
DONE
