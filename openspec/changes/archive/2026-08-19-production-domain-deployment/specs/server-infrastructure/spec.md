## ADDED Requirements

### Requirement: PostgreSQL installed and configured
PostgreSQL SHALL be installed on the server with a dedicated database and user for the Rock Slab application.

#### Scenario: PostgreSQL service running
- **WHEN** checking PostgreSQL service status
- **THEN** the service SHALL be active and listening on localhost:5432

#### Scenario: Database and user created
- **WHEN** deployment is complete
- **THEN** a database `rock_slab` and user `rock_slab_user` SHALL exist with a strong password

#### Scenario: Django connects to PostgreSQL
- **WHEN** the Django backend starts with DATABASE_URL configured
- **THEN** it SHALL connect successfully and run migrations

### Requirement: Redis installed and configured
Redis SHALL be installed on the server for the Django cache backend.

#### Scenario: Redis service running
- **WHEN** checking Redis service status
- **THEN** Redis SHALL be active and listening on localhost:6379

#### Scenario: Django cache connection
- **WHEN** the Django backend starts with REDIS_URL configured
- **THEN** it SHALL connect to Redis for caching

### Requirement: Firewall closes direct backend access
The server firewall SHALL only expose ports 22, 80, and 443. Port 8080 (and 8002, 5432, 6379) SHALL NOT be reachable from the internet.

#### Scenario: Required ports open
- **WHEN** checking firewall rules
- **THEN** ports 22, 80, 443 SHALL be allowed

#### Scenario: Backend port closed externally
- **WHEN** attempting to access http://47.97.43.28:8080 from outside the server
- **THEN** the connection SHALL be refused or blocked

### Requirement: Server software prerequisites installed
The server SHALL have Docker, Docker Compose, Node.js LTS, git, and certbot.

#### Scenario: Docker available
- **WHEN** running `docker --version` and `docker compose version`
- **THEN** both SHALL succeed

#### Scenario: Node.js available
- **WHEN** running `node --version`
- **THEN** an LTS version SHALL be installed

#### Scenario: certbot available
- **WHEN** running `certbot --version`
- **THEN** certbot SHALL be installed
