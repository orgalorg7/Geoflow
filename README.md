# GeoFlow!

GeoFlow is a no-code geospatial analysis platform. The current implementation
provides the Docker-first monorepo foundation, secure user authentication, and
project/AOI management together with the Phase 4 directed workflow builder: a
Next.js and MapLibre web application, FastAPI API, Celery worker,
PostgreSQL/PostGIS, Redis, rotating sessions, and the Phase 5 raster-processing
engine.

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

## Projects and areas of interest

Phase 3 includes user-owned project CRUD and PostGIS-backed polygon areas of
interest. Users can draw a polygon on a MapLibre map, drag its vertices to edit
it, or upload a `.geojson`/`.json` file containing one Polygon.

GeoFlow validates file size and type, GeoJSON structure, polygon geometry,
coordinate ranges, vertex complexity, and maximum area before saving anything.
Area is calculated geodesically in square kilometres.

To test the complete Phase 3 browser flow:

1. Sign in and create a project from http://localhost:3000/dashboard.
2. Open the project and click **Draw polygon**.
3. Click at least three map positions, name the area, and save it.
4. Click **Edit**, drag vertices, and save the changes.
5. Upload `docs/examples/cairo-aoi.geojson` and confirm both areas appear.
6. Sign in as a different user and confirm the first user's projects are hidden.

Development limits can be configured with `AOI_MAX_UPLOAD_BYTES`,
`AOI_MAX_VERTICES`, and `AOI_MAX_AREA_SQ_KM`.

## Analysis workflows

Phase 4 adds project-owned workflows stored as directed graphs. Each guided
workflow contains AOI, dataset, operation, and visualization nodes connected by
typed input/output ports. The API exposes supported datasets, bands,
operations, parameters, color ramps, and connection rules to the frontend.
The Phase 4 catalog contains Sentinel-2 Level-2A and NDVI; the later roadmap
phases add processing support and more datasets and indices.

Validation detects missing inputs or AOIs, invalid date windows, cycles,
unsupported connections, unsupported datasets or bands, and invalid operation
or visualization parameters. A valid workflow is marked executable; execution
itself begins in Phase 7.

To test the Phase 4 browser flow:

1. Sign in, create a project, and save at least one AOI.
2. Under **Analysis workflows**, click **Configure a workflow**.
3. Select Sentinel-2 Level-2A, a date range, cloud limit, and **NDVI**.
4. Choose the preview color ramp, value range, and opacity.
5. Click **Save and validate workflow**.
6. Confirm the page reports **Workflow is executable**.
7. Return to the project and confirm the saved workflow can be edited or
   deleted.

The protected workflow endpoints are documented at
http://localhost:8000/docs. Run `make test` to exercise graph validation,
workflow ownership, API persistence, and frontend graph construction.

## Geospatial processing engine

Phase 5 adds the independently testable `geoflow-geospatial-core` Python
package. It provides immutable raster and logical-band abstractions,
provider-neutral Sentinel-2 and Landsat band mappings, and implementations of
NDVI, NDWI, NDBI, and SAVI.

The engine propagates NoData masks, protects every index calculation from
division by zero, clips rasters to GeoJSON AOIs, transforms AOIs between
coordinate reference systems, and reprojects raster grids. It calculates
minimum, maximum, mean, standard deviation, valid-pixel count, and NoData-pixel
count.

Analytical results can be classified, written as Cloud Optimized GeoTIFFs, and
rendered as transparent color-ramp PNG previews. Preview creation never changes
the analytical raster values. The high-level artifact pipeline combines index
calculation, AOI clipping, statistics, optional classification, COG output, and
preview generation.

Run the deterministic local-raster tests with:

```bash
docker compose run --rm --no-deps api \
  python -m pytest /workspace/packages/geospatial-core/tests
```

These tests generate all fixture rasters in temporary directories and do not
contact a satellite provider. Real Sentinel-2 discovery begins in Phase 6, and
background execution begins in Phase 7.

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

The remaining empty package directories contain notes describing
responsibilities planned for later phases.
