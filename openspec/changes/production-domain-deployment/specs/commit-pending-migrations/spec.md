## ADDED Requirements

### Requirement: All migration files committed to git
Every Django migration file in the repository SHALL be tracked by git, so that `git pull` on the server brings the database schema in sync with the deployed code.

#### Scenario: Untracked migration files are added and committed
- **WHEN** checking git status before deployment
- **THEN** the following migration files SHALL be tracked and committed: assets/migrations/0004_add_fixedasset_model.py, assets/migrations/0005_*.py, organizations/migrations/0004_add_fixedasset_model.py, transfers/migrations/0006_add_recovery_fields.py, transfers/migrations/0007_*.py

#### Scenario: No untracked migrations remain
- **WHEN** running `git status` after committing
- **THEN** there SHALL be no `??` entries under any app's migrations/ directory

#### Scenario: Server receives migrations via git pull
- **WHEN** deploy.sh runs `git pull origin main` on the server
- **THEN** all 5 migration files SHALL exist on the server and `python manage.py migrate` SHALL apply them without "table already exists" or "column missing" errors
