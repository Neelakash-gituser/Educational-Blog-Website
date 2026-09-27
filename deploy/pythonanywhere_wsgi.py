"""WSGI file for PythonAnywhere.

Copy the contents of this file into the WSGI configuration file that the
**Web** tab links to (it lives at /var/www/<username>_pythonanywhere_com_wsgi.py),
replacing everything that is already there, then edit USERNAME below.

Settings themselves are read from the .env file in the project directory —
see deploy/pythonanywhere.md — so no secrets belong in here.
"""

import os
import sys

USERNAME = "yourusername"  # <- your PythonAnywhere username
PROJECT_DIR = f"/home/{USERNAME}/Educational-Blog-Website"

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
