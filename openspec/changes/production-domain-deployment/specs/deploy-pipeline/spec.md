## ADDED Requirements

### Requirement: deploy.sh Nginx reload command is correct
The deploy.sh script SHALL use the correct command to reload the host Nginx service.

#### Scenario: Nginx reload succeeds
- **WHEN** deploy.sh runs the Nginx reload step
- **THEN** it SHALL reload the host Nginx service (not attempt `docker exec root-nginx-1`, which references a non-existent container)

### Requirement: deploy.sh health check port matches backend
The deploy.sh health check SHALL target the same port the backend binds to.

#### Scenario: Health check port consistent
- **WHEN** deploy.sh runs the health check
- **THEN** it SHALL curl localhost:8002/api/health/ (matching the backend PORT=8002)

### Requirement: One-click deployment works
The deploy.sh script SHALL execute the full deployment cycle end-to-end.

#### Scenario: deploy.sh runs end-to-end
- **WHEN** executing `bash deploy.sh` from the project root on the server
- **THEN** all steps SHALL complete: git pull, docker build, migrate, collectstatic, npm build, container restart, nginx reload, health check

#### Scenario: Health check passes after deploy
- **WHEN** deploy.sh completes
- **THEN** the script SHALL report success and the health check SHALL return HTTP 200

### Requirement: Post-deployment verification
After deployment, verification SHALL confirm the system is fully operational via the domain.

#### Scenario: HTTPS via domain works
- **WHEN** deployment is complete
- **THEN** https://qhpanpan.top SHALL show the Rock Slab login page with a valid SSL certificate

#### Scenario: API health via domain works
- **WHEN** deployment is complete
- **THEN** https://qhpanpan.top/api/health/ SHALL return `{"status": "ok"}`

#### Scenario: Backend port not externally accessible
- **WHEN** attempting to access http://47.97.43.28:8080 from outside
- **THEN** the connection SHALL be refused (firewall closed)

### Requirement: Database backup established
PostgreSQL SHALL have a daily backup configured.

#### Scenario: Backup cron job exists
- **WHEN** checking crontab
- **THEN** a daily pg_dump job for the rock_slab database SHALL be configured
