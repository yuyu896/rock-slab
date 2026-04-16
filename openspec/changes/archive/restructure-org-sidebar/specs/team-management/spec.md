## ADDED Requirements

### Requirement: Team data model
The system SHALL provide a Team (行政组) model with fields: `name` (组名, required), `region` (FK→Region, required), `leader` (FK→User, optional, role=leader), `status` (active/inactive, default active), `created_at`, `updated_at`.

#### Scenario: Create team via API
- **WHEN** admin sends `POST /api/teams/` with `{"name": "行政一组", "region": "<regionId>"}`
- **THEN** the system SHALL create a Team record and return the serialized Team data with status 201

#### Scenario: Team belongs to region
- **WHEN** a Team is created with a region reference
- **THEN** the Team SHALL be queryable by `GET /api/teams/?region=<regionId>`

### Requirement: Team CRUD API
The system SHALL provide RESTful endpoints for Team management at `/api/teams/` with full CRUD (list, create, retrieve, update, delete). Only admin and manager roles SHALL be allowed to manage teams.

#### Scenario: List all teams
- **WHEN** user sends `GET /api/teams/`
- **THEN** the system SHALL return all teams with their region name, leader name, and member count

#### Scenario: Update team leader
- **WHEN** admin sends `PUT /api/teams/<id>/` with `{"leader": "<userId>"}`
- **THEN** the system SHALL assign the user as team leader (if user role is `leader`) and return updated data

#### Scenario: Delete team
- **WHEN** admin sends `DELETE /api/teams/<id>/`
- **THEN** the system SHALL delete the team and set all members' `team` field to null

#### Scenario: Non-admin cannot create team
- **WHEN** a staff user sends `POST /api/teams/`
- **THEN** the system SHALL return 403 Forbidden

### Requirement: Team management UI
The system SHALL display team management within the organization module. Each region in the sidebar SHALL show its teams. Admins SHALL be able to create, edit, and delete teams via modal forms.

#### Scenario: Create team from sidebar
- **WHEN** admin right-clicks or uses action button on a region node
- **THEN** the system SHALL show a create team modal pre-filled with the region, with fields: team name and leader selection

#### Scenario: Edit team
- **WHEN** admin clicks edit on a team node
- **THEN** the system SHALL show an edit modal pre-filled with current team data

#### Scenario: Delete team with members
- **WHEN** admin deletes a team that has members
- **THEN** the system SHALL show confirmation "该组下有 N 名成员，删除后成员将变为未分组，确定删除？", and on confirm SHALL delete the team and unassign members

### Requirement: User-team association
User model SHALL have a `team` FK field (FK→Team, nullable). Users with `role=leader` or `role=staff` SHALL be assignable to a team. When a user is set as `Team.leader`, the system SHALL also set the user's `team` field to that team.

#### Scenario: Assign user to team
- **WHEN** admin sets a user's team via `PUT /api/users/<id>/` with `{"team": "<teamId>"}`
- **THEN** the system SHALL associate the user with the specified team

#### Scenario: Set team leader auto-assigns team
- **WHEN** admin sets a user as team leader via `PUT /api/teams/<id>/` with `{"leader": "<userId>"}`
- **THEN** the system SHALL also update the leader user's `team` field to point to this team
