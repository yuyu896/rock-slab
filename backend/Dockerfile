FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies. The production host has a slow route to the
# default Debian CDN, so keep the mirror configurable and use the verified
# mainland mirror by default.
ARG DEBIAN_MIRROR=https://mirrors.163.com/debian
ARG DEBIAN_SECURITY_MIRROR=https://mirrors.163.com/debian-security
RUN sed -i \
      -e "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
      -e "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
      /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=2 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 update \
    && apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=2 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (阿里云 PyPI 镜像，国内服务器加速)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    -r requirements.txt

# Copy application code
COPY . .

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

# Collect static files
RUN DJANGO_SETTINGS_MODULE=rock_slab.settings.production \
    SECRET_KEY=build-time-dummy \
    DATABASE_URL=sqlite:///tmp/dummy.db \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Create media directory
RUN mkdir -p /app/media

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
