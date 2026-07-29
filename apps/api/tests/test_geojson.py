import json

import pytest

from geoflow_api.projects.geojson import (
    GeoJSONValidationError,
    parse_geojson_upload,
    validate_polygon_geojson,
)

SMALL_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [31.20, 30.00],
            [31.30, 30.00],
            [31.30, 30.10],
            [31.20, 30.10],
            [31.20, 30.00],
        ]
    ],
}


def test_valid_polygon_returns_geodesic_area_and_normalized_geojson() -> None:
    result = validate_polygon_geojson(
        SMALL_POLYGON, max_vertices=100, max_area_sq_km=10_000
    )

    assert result.geojson["type"] == "Polygon"
    assert result.vertex_count == 5
    assert 100 < result.area_sq_km < 110


def test_single_feature_collection_is_supported() -> None:
    result = validate_polygon_geojson(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Cairo"},
                    "geometry": SMALL_POLYGON,
                }
            ],
        },
        max_vertices=100,
        max_area_sq_km=10_000,
    )

    assert result.geojson["type"] == "Polygon"


@pytest.mark.parametrize(
    ("geometry", "message"),
    [
        (
            {
                "type": "Polygon",
                "coordinates": [
                    [[31.0, 30.0], [31.1, 30.1], [31.0, 30.1], [31.1, 30.0], [31.0, 30.0]]
                ],
            },
            "invalid",
        ),
        (
            {
                "type": "Polygon",
                "coordinates": [
                    [[181.0, 30.0], [31.1, 30.0], [31.1, 30.1], [181.0, 30.0]]
                ],
            },
            "Longitude",
        ),
        (
            {
                "type": "LineString",
                "coordinates": [[31.0, 30.0], [31.1, 30.1]],
            },
            "Polygon",
        ),
    ],
)
def test_invalid_geometries_are_rejected(
    geometry: dict[str, object], message: str
) -> None:
    with pytest.raises(GeoJSONValidationError, match=message):
        validate_polygon_geojson(
            geometry, max_vertices=100, max_area_sq_km=10_000
        )


def test_vertex_complexity_limit_is_enforced() -> None:
    with pytest.raises(GeoJSONValidationError, match="limit is 4"):
        validate_polygon_geojson(
            SMALL_POLYGON, max_vertices=4, max_area_sq_km=10_000
        )


def test_maximum_area_is_enforced() -> None:
    with pytest.raises(GeoJSONValidationError, match="the limit is 10.00"):
        validate_polygon_geojson(
            SMALL_POLYGON, max_vertices=100, max_area_sq_km=10
        )


def test_upload_validates_extension_content_and_size() -> None:
    encoded = json.dumps(SMALL_POLYGON).encode()
    result = parse_geojson_upload(
        filename="cairo.geojson",
        content_type="application/geo+json",
        content=encoded,
        max_bytes=10_000,
        max_vertices=100,
        max_area_sq_km=10_000,
    )
    assert result.area_sq_km > 100

    with pytest.raises(GeoJSONValidationError, match=".geojson or .json"):
        parse_geojson_upload(
            filename="cairo.txt",
            content_type="text/plain",
            content=encoded,
            max_bytes=10_000,
            max_vertices=100,
            max_area_sq_km=10_000,
        )

    with pytest.raises(GeoJSONValidationError, match="exceeds"):
        parse_geojson_upload(
            filename="cairo.geojson",
            content_type="application/geo+json",
            content=encoded,
            max_bytes=10,
            max_vertices=100,
            max_area_sq_km=10_000,
        )
