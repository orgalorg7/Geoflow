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
