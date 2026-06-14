## ADDED Requirements

### Requirement: Frontend builds for production
The Vue 3 frontend SHALL build successfully with production settings (already verified: vue-tsc 0 errors, Transfer type complete).

#### Scenario: npm build succeeds
- **WHEN** running `npm run build` in the frontend directory
- **THEN** a dist/ directory SHALL be created with index.html and optimized assets, exit code 0

#### Scenario: Build uses same-origin API
- **WHEN** the frontend is built with VITE_API_BASE_URL empty
- **THEN** API requests SHALL use relative paths (/api/*) resolved by the Nginx reverse proxy

### Requirement: Frontend static files served by Nginx
The built frontend SHALL be served by Nginx from the configured root directory.

#### Scenario: Frontend index.html accessible
- **WHEN** accessing https://qhpanpan.top/
- **THEN** the Vue SPA index.html SHALL be served with HTTP 200

#### Scenario: Client-side routing works
- **WHEN** directly navigating to https://qhpanpan.top/login or any SPA route
- **THEN** Nginx SHALL serve index.html and the Vue router SHALL handle the route (no 404)

### Requirement: Frontend communicates with backend API
The frontend SHALL successfully call the backend API through Nginx.

#### Scenario: Login API call succeeds
- **WHEN** a user submits login credentials on https://qhpanpan.top/login
- **THEN** the POST /api request SHALL reach the backend and return a valid token response
