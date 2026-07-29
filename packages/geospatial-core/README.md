# GeoFlow geospatial core

Provider-neutral, independently testable raster processing for GeoFlow.

## Capabilities

- Immutable georeferenced raster and logical-band abstractions
- Sentinel-2 Level-2A and Landsat 8/9 Level-2 band mappings
- NDVI, NDWI, NDBI, and SAVI calculations
- Combined NoData propagation and division-by-zero protection
- AOI clipping with automatic geometry CRS transformation
- Raster reprojection with validity-mask preservation
- Minimum, maximum, mean, standard deviation, and pixel counts
- Optional index classification and classified previews
- Analytical Cloud Optimized GeoTIFF output
- Transparent color-ramp PNG previews that do not modify source values
- A high-level local index-to-artifacts pipeline

## Run tests

From the repository root:

```bash
make test
```

To run only this package after installing its development dependencies:

```bash
python -m pip install -e "packages/geospatial-core[dev]"
python -m pytest packages/geospatial-core/tests
```

The tests generate small deterministic GeoTIFF fixtures in temporary
directories. They do not download imagery or require external services.
