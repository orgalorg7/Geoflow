import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyproj import Geod
from shapely.geometry import Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.validation import explain_validity

WGS84_GEOD = Geod(ellps="WGS84")
ALLOWED_UPLOAD_SUFFIXES = {".geojson", ".json"}
ALLOWED_CONTENT_TYPES = {
    "",
    "application/geo+json",
    "application/json",
    "application/octet-stream",
    "text/plain",
}


class GeoJSONValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedPolygon:
    polygon: Polygon
    geojson: dict[str, Any]
    area_sq_km: float
    vertex_count: int


def validate_polygon_geojson(
    document: dict[str, Any],
    *,
    max_vertices: int,
    max_area_sq_km: float,
) -> ValidatedPolygon:
    geometry = _extract_geometry(document)
    if geometry.get("type") != "Polygon":
        raise GeoJSONValidationError("Only GeoJSON Polygon geometries are supported")

    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        raise GeoJSONValidationError("Polygon coordinates must contain at least one ring")

    vertex_count = 0
    for ring in coordinates:
        if not isinstance(ring, list) or len(ring) < 4:
            raise GeoJSONValidationError(
                "Every polygon ring must contain at least four positions"
            )
        if ring[0] != ring[-1]:
            raise GeoJSONValidationError("Polygon rings must be closed")
        for position in ring:
            _validate_position(position)
            vertex_count += 1

    if vertex_count > max_vertices:
        raise GeoJSONValidationError(
            f"Polygon has {vertex_count} vertices; the limit is {max_vertices}"
        )

    try:
        candidate = shape(geometry)
    except (TypeError, ValueError, KeyError) as exc:
        raise GeoJSONValidationError("Polygon coordinates are malformed") from exc

    if not isinstance(candidate, Polygon):
        raise GeoJSONValidationError("Only GeoJSON Polygon geometries are supported")
    if candidate.is_empty:
        raise GeoJSONValidationError("Polygon geometry cannot be empty")
    if not candidate.is_valid:
        raise GeoJSONValidationError(
            f"Polygon geometry is invalid: {explain_validity(candidate)}"
        )

    area_sq_km = abs(WGS84_GEOD.geometry_area_perimeter(candidate)[0]) / 1_000_000
    if not math.isfinite(area_sq_km) or area_sq_km <= 0:
        raise GeoJSONValidationError("Polygon must enclose a measurable area")
    if area_sq_km > max_area_sq_km:
        raise GeoJSONValidationError(
            f"Polygon area is {area_sq_km:,.2f} km²; "
            f"the limit is {max_area_sq_km:,.2f} km²"
        )

    normalized = orient(candidate, sign=1.0)
    return ValidatedPolygon(
        polygon=normalized,
        geojson=dict(mapping(normalized)),
        area_sq_km=area_sq_km,
        vertex_count=vertex_count,
    )


def parse_geojson_upload(
    *,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    max_bytes: int,
    max_vertices: int,
    max_area_sq_km: float,
) -> ValidatedPolygon:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise GeoJSONValidationError("Upload must use a .geojson or .json file")
    if (content_type or "").lower() not in ALLOWED_CONTENT_TYPES:
        raise GeoJSONValidationError("Upload must be a GeoJSON or JSON file")
    if not content:
        raise GeoJSONValidationError("Uploaded GeoJSON file is empty")
    if len(content) > max_bytes:
        raise GeoJSONValidationError(
            f"Uploaded file exceeds the {max_bytes // 1_000_000} MB limit"
        )
    try:
        decoded = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GeoJSONValidationError("Uploaded file is not valid UTF-8 JSON") from exc
    if not isinstance(decoded, dict):
        raise GeoJSONValidationError("GeoJSON root must be an object")
    return validate_polygon_geojson(
        decoded,
        max_vertices=max_vertices,
        max_area_sq_km=max_area_sq_km,
    )


def _extract_geometry(document: dict[str, Any]) -> dict[str, Any]:
    object_type = document.get("type")
    if object_type == "Feature":
        geometry = document.get("geometry")
    elif object_type == "FeatureCollection":
        features = document.get("features")
        if not isinstance(features, list) or len(features) != 1:
            raise GeoJSONValidationError(
                "FeatureCollection must contain exactly one Polygon feature"
            )
        feature = features[0]
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise GeoJSONValidationError("FeatureCollection contains an invalid feature")
        geometry = feature.get("geometry")
    elif object_type == "Polygon":
        geometry = document
    else:
        raise GeoJSONValidationError(
            "GeoJSON must be a Polygon, Feature, or single-feature FeatureCollection"
        )
    if not isinstance(geometry, dict):
        raise GeoJSONValidationError("GeoJSON feature must contain a geometry object")
    return geometry


def _validate_position(position: Any) -> None:
    if not isinstance(position, list) or len(position) != 2:
        raise GeoJSONValidationError(
            "Every coordinate position must contain longitude and latitude"
        )
    longitude, latitude = position
    if (
        isinstance(longitude, bool)
        or isinstance(latitude, bool)
        or not isinstance(longitude, (int, float))
        or not isinstance(latitude, (int, float))
        or not math.isfinite(longitude)
        or not math.isfinite(latitude)
    ):
        raise GeoJSONValidationError("Coordinate values must be finite numbers")
    if not -180 <= longitude <= 180:
        raise GeoJSONValidationError("Longitude values must be between -180 and 180")
    if not -90 <= latitude <= 90:
        raise GeoJSONValidationError("Latitude values must be between -90 and 90")
