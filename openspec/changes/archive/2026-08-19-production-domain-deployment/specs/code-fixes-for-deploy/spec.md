## ADDED Requirements

### Requirement: CSRF_TRUSTED_ORIGINS configured for production
The production Django settings SHALL define CSRF_TRUSTED_ORIGINS with both the apex domain and www subdomain over HTTPS.

#### Scenario: CSRF validation passes for HTTPS requests
- **WHEN** a POST/PUT/DELETE request is made from https://qhpanpan.top with valid credentials
- **THEN** Django SHALL accept the request without a 403 CSRF rejection

#### Scenario: CSRF validation passes for www subdomain
- **WHEN** a POST/PUT/DELETE request is made from https://www.qhpanpan.top
- **THEN** Django SHALL accept the request without a 403 CSRF rejection

### Requirement: ALLOWED_HOSTS includes both domain variants
The production ALLOWED_HOSTS SHALL include both qhpanpan.top and www.qhpanpan.top.

#### Scenario: www subdomain requests accepted
- **WHEN** a request arrives with Host: www.qhpanpan.top
- **THEN** Django SHALL serve it (not return 400 DisallowedHost)

### Requirement: Backend port is consistent across all configs
The backend port SHALL be 8002 everywhere: .env PORT, gunicorn bind, docker-compose healthcheck, nginx proxy_pass, and deploy.sh health curl.

#### Scenario: Gunicorn binds to 8002
- **WHEN** the backend container starts with PORT=8002
- **THEN** gunicorn SHALL listen on 0.0.0.0:8002

#### Scenario: Healthcheck targets 8002
- **WHEN** docker-compose runs the healthcheck
- **THEN** it SHALL check localhost:8002/api/health/ (not 8000)

#### Scenario: Nginx proxies to 8002
- **WHEN** Nginx receives /api/ requests
- **THEN** it SHALL proxy_pass to http://127.0.0.1:8002

### Requirement: Backend entrypoint runs migrations before startup
A backend entrypoint.sh SHALL run database migrations before starting Gunicorn.

#### Scenario: Migrations run on container start
- **WHEN** the Docker backend container starts
- **THEN** `python manage.py migrate --noinput` SHALL execute before Gunicorn starts

#### Scenario: Migration failure stops startup
- **WHEN** database migrations fail
- **THEN** the container SHALL exit with an error code (not silently start with missing schema)

### Requirement: SECURE_SSL_REDIRECT disabled in production env
The production .env SHALL set SECURE_SSL_REDIRECT=False because Nginx handles HTTP-to-HTTPS redirect.

#### Scenario: Health check over HTTP succeeds
- **WHEN** a healthcheck sends an HTTP request to localhost:8002/api/health/
- **THEN** Gunicorn SHALL return 200, not a 301 redirect to HTTPS

#### Scenario: External HTTP requests still redirected
- **WHEN** an external request arrives at http://qhpanpan.top
- **THEN** Nginx SHALL return 301 redirect to https://qhpanpan.top
