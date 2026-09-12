# Works on Fly.io, Railway, Koyeb, Google Cloud Run — anywhere that takes a container.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Static files are baked into the image; whitenoise serves them at runtime.
RUN SECRET_KEY=build-only DEBUG=False python manage.py collectstatic --no-input

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --no-input && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers 2"]
