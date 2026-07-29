# GeoFlow architecture

GeoFlow uses independently deployable web, API, and worker applications.

```text
Browser -> Next.js web -> FastAPI API -> PostgreSQL/PostGIS
                            |
                            +---------> Redis -> Celery worker
```

- The API owns synchronous request validation and persistence.
- The worker will own expensive geospatial processing.
- Redis separates HTTP requests from background jobs.
- PostgreSQL/PostGIS is the system of record for users, projects, workflows,
  jobs, and geometries.
- Storage is mounted as a distinct volume so a local adapter can later be
  replaced with S3 or MinIO.

The liveness endpoint proves that the API process is running. The readiness
endpoint checks PostgreSQL and Redis and returns HTTP 503 when either dependency
is unavailable.

## Implemented request paths

Authentication uses short-lived access cookies and rotating refresh cookies.
Only hashed refresh tokens are persisted.

Project and AOI requests follow this path:

```text
Protected FastAPI route
  -> ownership-aware project service
  -> GeoJSON polygon validation
  -> SQLAlchemy repository
  -> PostgreSQL/PostGIS (SRID 4326)
```

Project ownership is checked before AOIs are read or changed. Unauthorized
project IDs return the same not-found response as nonexistent IDs. Polygon
areas are computed geodesically with WGS84, while PostGIS stores validated
geometry and provides a GiST spatial index for future searches.

Workflow requests follow a separate ownership-aware service path:

```text
Guided builder
  -> workflow CRUD API
  -> workflow / node / edge tables
  -> directed-graph validator
       -> node type and port rules
       -> AOI and dataset checks
       -> date, band, and parameter checks
       -> cycle detection
```

The graph is stored independently of its validation result so the user can save
an incomplete configuration and receive actionable errors. Structural
constraints still prevent duplicate node keys, dangling edges, and multiple
connections to one target input. A workflow is executable only when the
validator returns no errors.

The current guided graph has four node types:

```text
AOI.geometry ──> Dataset.aoi
      │
      └────────> Operation.aoi
Dataset.raster ─> Operation.raster ─> Visualization.raster
```

Workflow definitions are served by the protected
`GET /api/v1/workflow-definitions` endpoint, keeping the frontend form aligned
with backend dataset, band, operation, parameter, visualization, and connection
rules.
