FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files
RUN DJANGO_SETTINGS_MODULE=rock_slab.settings.production \
    SECRET_KEY=build-time-dummy \
    DATABASE_URL=sqlite:///tmp/dummy.db \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Create media directory
RUN mkdir -p /app/media

EXPOSE 8000

CMD ["gunicorn", "rock_slab.wsgi:application", "-c", "gunicorn.conf.py"]
