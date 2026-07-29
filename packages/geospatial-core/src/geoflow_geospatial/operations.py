from typing import Any

import numpy as np
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from rasterio.mask import mask as raster_mask
from rasterio.warp import calculate_default_transform, reproject, transform_geom

from geoflow_geospatial.errors import GeometryOutsideRasterError
from geoflow_geospatial.raster import Raster


def clip_raster(
    raster: Raster,
    geometry: dict[str, Any],
    *,
    geometry_crs: CRS | str = "EPSG:4326",
) -> Raster:
    """Crop and mask a raster to a GeoJSON geometry."""

    source_crs = CRS.from_user_input(geometry_crs)
    transformed_geometry = geometry
    if source_crs != raster.crs:
        transformed_geometry = transform_geom(
            source_crs,
            raster.crs,
            geometry,
            precision=12,
        )

    profile = {
        "driver": "GTiff",
        "height": raster.height,
        "width": raster.width,
        "count": 1,
        "dtype": "float32",
        "crs": raster.crs,
        "transform": raster.transform,
        "nodata": raster.nodata,
    }
    try:
        with MemoryFile() as memory:
            with memory.open(**profile) as dataset:
                dataset.write(raster.filled(), 1)
                dataset.write_mask((~raster.mask).astype(np.uint8) * 255)
                clipped, clipped_transform = raster_mask(
                    dataset,
                    [transformed_geometry],
                    crop=True,
                    filled=False,
                )
    except ValueError as exc:
        raise GeometryOutsideRasterError("AOI does not overlap the raster") from exc

    band = clipped[0]
    return Raster(
        np.asarray(band.filled(raster.nodata), dtype=np.float32),
        transform=clipped_transform,
        crs=raster.crs,
        mask=np.ma.getmaskarray(band),
        nodata=raster.nodata,
        name=raster.name,
    )


def reproject_raster(
    raster: Raster,
    destination_crs: CRS | str,
    *,
    resolution: float | tuple[float, float] | None = None,
    resampling: Resampling = Resampling.bilinear,
) -> Raster:
    """Reproject a raster and its validity mask to a new pixel grid."""

    target_crs = CRS.from_user_input(destination_crs)
    if target_crs == raster.crs and resolution is None:
        return Raster(
            raster.data,
            transform=raster.transform,
            crs=raster.crs,
            mask=raster.mask,
            nodata=raster.nodata,
            name=raster.name,
        )

    transform, width, height = calculate_default_transform(
        raster.crs,
        target_crs,
        raster.width,
        raster.height,
        *raster.bounds,
        resolution=resolution,
    )
    destination = np.full((height, width), raster.nodata, dtype=np.float32)
    reproject(
        source=raster.filled(),
        destination=destination,
        src_transform=raster.transform,
        src_crs=raster.crs,
        src_nodata=raster.nodata,
        dst_transform=transform,
        dst_crs=target_crs,
        dst_nodata=raster.nodata,
        resampling=resampling,
    )

    source_validity = (~raster.mask).astype(np.uint8)
    destination_validity = np.zeros((height, width), dtype=np.uint8)
    reproject(
        source=source_validity,
        destination=destination_validity,
        src_transform=raster.transform,
        src_crs=raster.crs,
        dst_transform=transform,
        dst_crs=target_crs,
        resampling=Resampling.nearest,
    )
    destination_mask = (
        (destination_validity == 0)
        | ~np.isfinite(destination)
        | np.isclose(destination, raster.nodata)
    )
    return Raster(
        destination,
        transform=transform,
        crs=target_crs,
        mask=destination_mask,
        nodata=raster.nodata,
        name=raster.name,
    )
