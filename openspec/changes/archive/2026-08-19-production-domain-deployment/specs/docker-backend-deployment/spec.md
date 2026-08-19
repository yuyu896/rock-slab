## ADDED Requirements

### Requirement: Backend Docker image builds successfully
The Docker image SHALL build from backend/Dockerfile without errors.

#### Scenario: Docker build completes
- **WHEN** running `docker compose build backend`
- **THEN** the image SHALL build with all Python dependencies installed

### Requirement: Production environment variables configured
A .env file SHALL exist at /root/rock-slab/.env with all required production values.

#### Scenario: Required environment variables present
- **WHEN** the .env file is checked
- **THEN** it SHALL contain: SECRET_KEY (strong random value), DJANGO_SETTINGS_MODULE=rock_slab.settings.production, ALLOWED_HOSTS=qhpanpan.top,www.qhpanpan.top, DATABASE_URL, REDIS_URL, PORT=8002, SECURE_SSL_REDIRECT=False

#### Scenario: Secret key is secure
- **WHEN** checking SECRET_KEY
- **THEN** it SHALL be at least 50 random characters (not a default/example value)

### Requirement: Database migrations run on deploy
Django migrations SHALL be executed during deployment (via entrypoint.sh).

#### Scenario: Migrations apply successfully
- **WHEN** the backend container starts
- **THEN** all pending migrations (including assets 0004/0005, organizations 0004, transfers 0006/0007) SHALL be applied without errors

#### Scenario: Superuser can be created
- **WHEN** running the create_superuser management command
- **THEN** an admin user SHALL be created for initial access

### Requirement: Backend container runs and passes health check
The Docker backend container SHALL start and respond to health checks.

#### Scenario: Container starts
- **WHEN** running `docker compose up -d backend`
- **THEN** the container SHALL be in "running" state

#### Scenario: Health check responds
- **WHEN** accessing http://localhost:8002/api/health/
- **THEN** a 200 response with `{"status": "ok"}` SHALL be returned

### Requirement: Static files available to Nginx
Django collectstatic output SHALL be accessible at the host path Nginx serves.

#### Scenario: Host staticfiles directory populated
- **WHEN** deployment completes
- **THEN** /root/rock-slab/backend/staticfiles/ SHALL contain collected static files (admin CSS/JS etc.) that Nginx serves at /static/
