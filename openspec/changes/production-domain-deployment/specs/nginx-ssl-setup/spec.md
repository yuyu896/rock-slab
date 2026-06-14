## ADDED Requirements

### Requirement: Nginx serves Rock Slab as a new virtual host
Nginx SHALL add a virtual host for qhpanpan.top serving the Rock Slab frontend and reverse-proxying the API, while leaving the existing AI销售教练 project untouched.

#### Scenario: HTTP to HTTPS redirect
- **WHEN** a request is made to http://qhpanpan.top
- **THEN** Nginx SHALL return a 301 redirect to https://qhpanpan.top

#### Scenario: API reverse proxy
- **WHEN** a request is made to https://qhpanpan.top/api/*
- **THEN** Nginx SHALL proxy to http://127.0.0.1:8002 and return the response

#### Scenario: Existing project still works
- **WHEN** accessing the server via its existing access method (IP) after adding the vhost
- **THEN** the AI销售教练 project SHALL remain accessible (server_name separation)

### Requirement: Valid SSL certificate issued for the domain
A valid Let's Encrypt SSL certificate SHALL be issued for qhpanpan.top (and www), replacing the currently broken certificate.

#### Scenario: HTTPS handshake succeeds via domain
- **WHEN** accessing https://qhpanpan.top
- **THEN** the SSL handshake SHALL succeed and the browser SHALL show a valid certificate (no warnings, no curl exit 35)

#### Scenario: Certificate covers both hostnames
- **WHEN** the certificate is issued
- **THEN** it SHALL cover qhpanpan.top and www.qhpanpan.top

#### Scenario: Certificate auto-renewal
- **WHEN** certbot renewal runs
- **THEN** certificates nearing expiry SHALL auto-renew and Nginx reload

### Requirement: SPA and static file serving
Nginx SHALL serve the SPA with fallback and serve static/media files from the correct paths.

#### Scenario: Media files served
- **WHEN** a request is made to https://qhpanpan.top/media/*
- **THEN** Nginx SHALL serve files from /root/rock-slab/backend/media/

#### Scenario: Backend static files served
- **WHEN** a request is made to https://qhpanpan.top/static/*
- **THEN** Nginx SHALL serve files from /root/rock-slab/backend/staticfiles/

#### Scenario: SPA fallback
- **WHEN** a request is made to any non-file path
- **THEN** Nginx SHALL serve /root/rock-slab/frontend/dist/index.html

### Requirement: Security headers configured
Nginx SHALL set HSTS, nosniff, frame-options, and XSS-protection headers on HTTPS responses.

#### Scenario: HSTS header set
- **WHEN** a response is served over HTTPS
- **THEN** Strict-Transport-Security with max-age >= 31536000 SHALL be present
