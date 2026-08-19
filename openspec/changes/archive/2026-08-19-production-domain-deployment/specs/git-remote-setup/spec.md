## ADDED Requirements

### Requirement: Git remote configured for deployment
The project SHALL have a git remote (origin) configured so that deploy.sh's `git pull origin main` works on the server.

#### Scenario: Git remote exists
- **WHEN** running `git remote -v`
- **THEN** an origin remote SHALL be listed pointing to a reachable repository

#### Scenario: Server can pull latest code
- **WHEN** deploy.sh runs `git pull origin main` on the server
- **THEN** the latest code (including all migrations) SHALL be pulled successfully

#### Scenario: All code pushed to remote
- **WHEN** the local repository is pushed
- **THEN** all committed files including the 5 migration files SHALL exist on the remote
