# GeoFlow

GeoFlow is a no-code geospatial analysis platform. Phase 1 provides the
Docker-first monorepo foundation: a Next.js web application, FastAPI API,
Celery worker, PostgreSQL/PostGIS, and Redis.

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
   - API documentation: http://localhost:8000/docs
   - API readiness: http://localhost:8000/api/v1/health/ready

The API container applies database migrations before starting.

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

The empty package directories contain notes describing the responsibilities
planned for later phases. Phase 1 intentionally contains no authentication,
project, workflow, or raster-processing implementations.
