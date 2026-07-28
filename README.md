# GeoFlow

GeoFlow is a no-code geospatial analysis platform. The current implementation
provides the Docker-first monorepo foundation plus Phase 2 user authentication:
a Next.js web application, FastAPI API, Celery worker, PostgreSQL/PostGIS,
Redis, rotating sessions, and a protected dashboard.

## Prerequisites

- Docker Desktop with Docker Compose
- Optional for running tools outside Docker: Node.js 20.9+ and Python 3.11+

## Start the platform

1. Copy `.env.example` to `.env`.
2. Change the development passwords if the services will be reachable outside
   your machine.
3. Run `make up`, or `docker compose up --build` on systems without Make.
4. Open:
   - Web application: http://localhost:3000
   - Registration: http://localhost:3000/register
   - Login: http://localhost:3000/login
   - API documentation: http://localhost:8000/docs
   - API readiness: http://localhost:8000/api/v1/health/ready

The API container applies database migrations before starting.

## Authentication

Phase 2 includes registration, login, short-lived access tokens, refresh-token
rotation, logout, current-user lookup, and protected routes. Access and refresh
tokens are delivered in HTTP-only cookies, and only refresh-token hashes are
stored in PostgreSQL.

For local development, replace `AUTH_SECRET_KEY` in `.env` with a long random
value if the application will be reachable by other machines. Production
deployments must also enable `AUTH_COOKIE_SECURE`.

To test the complete browser flow:

1. Open http://localhost:3000/register and create an account.
2. Confirm that registration opens `/dashboard`.
3. Log out and confirm that `/dashboard` redirects to `/login`.
4. Sign in again and reload `/dashboard` to confirm session restoration.

## Common commands

| Command | Purpose |
| --- | --- |
| `make setup` | Install local development dependencies |
| `make up` | Build and start the complete stack |
| `make down` | Stop the stack |
| `make migrate` | Apply database migrations |
| `make test` | Run Python and web tests |
| `make lint` | Run Python linting and TypeScript checks |
| `make format` | Format source files |
| `make logs` | Follow service logs |

## Repository layout

```text
apps/
  api/       FastAPI HTTP service and migrations
  web/       Next.js user interface
  worker/    Celery background worker
packages/
  config/    Shared Python environment configuration
  shared-types/
  workflow-engine/
  geospatial-core/
infrastructure/
  docker/
docs/
```

The empty package directories contain notes describing responsibilities planned
for later phases. Project, workflow, and raster-processing implementations begin
in Phases 3 through 5.
