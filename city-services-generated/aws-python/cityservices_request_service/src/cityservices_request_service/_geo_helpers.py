"""Geo helpers for CruftFree Geo builtin methods.

Pure stdlib implementations:
- GeoJSON feature conversion
- GeoJSON centroid computation
"""

from __future__ import annotations

import math

from fastapi import HTTPException


def _geo_to_geojson(
    features: list[dict[str, object]], feature_type: str
) -> list[dict[str, object]]:
    """Convert parsed geospatial feature dicts to GeoJSON Feature objects.

    Each input dict must have ``latitude`` and ``longitude`` keys (or ``lat``/``lng``).
    The ``feature_type`` is stored in ``properties.featureType``.

    Args:
        features: List of parsed feature dicts with coordinate fields.
        feature_type: Label for the feature type (e.g., ``"warehouse"``, ``"store"``).

    Returns:
        List of GeoJSON Feature dicts.
    """
    result: list[dict[str, object]] = []
    for feat in features:
        lat = feat.get("latitude") or feat.get("lat")
        lng = feat.get("longitude") or feat.get("lng")
        if lat is None or lng is None:
            continue
        geojson_feat: dict[str, object] = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(lng), float(lat)],
            },
            "properties": {
                "featureType": feature_type,
                **{
                    k: v
                    for k, v in feat.items()
                    if k not in ("latitude", "longitude", "lat", "lng")
                },
            },
        }
        result.append(geojson_feat)
    return result


def _geo_centroid(geometry: object) -> list[float]:
    """Compute the centroid ``[lat, lng]`` of a GeoJSON geometry.

    Supports Point, Polygon, and MultiPolygon geometry types.  For polygons the
    centroid is the arithmetic mean of the exterior ring coordinates.  For
    multi-polygons it is the area-weighted average across all polygons (using
    the Shoelace formula as a proxy for relative area); when every polygon has
    zero area it is the mean of the first polygon's exterior ring.

    Args:
        geometry: GeoJSON geometry object with ``type`` and ``coordinates``.

    Returns:
        ``[latitude, longitude]`` in WGS84 degrees.

    Raises:
        HTTPException: Status 422 -- the geometry is caller
            input -- when it is not an object, its coordinates are missing, a ring or
            position is empty or malformed, or its type is not one of Point, Polygon
            or MultiPolygon.
    """
    if not isinstance(geometry, dict):
        raise HTTPException(
            status_code=422,
            detail="GeoJSON geometry must be an object",
        )
    geom_type = str(geometry.get("type") or "")
    coords = geometry.get("coordinates")
    if coords is None:
        raise HTTPException(
            status_code=422,
            detail="GeoJSON geometry missing 'coordinates'",
        )

    if geom_type == "Point":
        lng, lat = _geo_position(coords)
        return [lat, lng]

    if geom_type == "Polygon":
        return _ring_centroid(_ring_positions(_geo_parts(coords, "polygon")[0]))

    if geom_type == "MultiPolygon":
        polygons = _geo_parts(coords, "multipolygon")
        total_area = 0.0
        weighted_lat = 0.0
        weighted_lng = 0.0
        for polygon in polygons:
            ring = _ring_positions(_geo_parts(polygon, "polygon")[0])
            clat, clng = _ring_centroid(ring)
            area = abs(_ring_signed_area(ring))
            total_area += area
            weighted_lat += clat * area
            weighted_lng += clng * area
        if total_area == 0.0:
            # Every polygon has zero area: the first polygon's ring mean.
            return _ring_centroid(
                _ring_positions(_geo_parts(polygons[0], "polygon")[0])
            )
        return [weighted_lat / total_area, weighted_lng / total_area]

    raise HTTPException(
        status_code=422,
        detail=(
            f"Unsupported geometry type '{geom_type}' for centroid. "
            f"Expected Point, Polygon, or MultiPolygon."
        ),
    )


def _geo_parts(value: object, what: str) -> list[object]:
    """*value* as the non-empty GeoJSON array it must be."""
    if isinstance(value, list) and value:
        return value
    raise HTTPException(
        status_code=422,
        detail=f"GeoJSON {what} must be a non-empty array",
    )


def _geo_position(value: object) -> list[float]:
    """``[lng, lat]`` of one GeoJSON position: two finite numbers."""
    if (
        isinstance(value, list)
        and len(value) >= 2
        and all(
            isinstance(axis, (int, float))
            and not isinstance(axis, bool)
            and math.isfinite(axis)
            for axis in value[:2]
        )
    ):
        return [float(value[0]), float(value[1])]
    raise HTTPException(
        status_code=422,
        detail="GeoJSON position must be an array of at least two finite numbers",
    )


def _ring_positions(ring: object) -> list[list[float]]:
    """The ``[lng, lat]`` positions of a coordinate ring."""
    return [_geo_position(position) for position in _geo_parts(ring, "coordinate ring")]


def _ring_centroid(ring: list[list[float]]) -> list[float]:
    """Compute the centroid ``[lat, lng]`` of a coordinate ring (arithmetic mean)."""
    n = len(ring)
    total_lng = sum(pt[0] for pt in ring)
    total_lat = sum(pt[1] for pt in ring)
    return [total_lat / n, total_lng / n]


def _ring_signed_area(ring: list[list[float]]) -> float:
    """Shoelace formula signed area for a coordinate ring (in coordinate units)."""
    n = len(ring)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += ring[i][0] * ring[j][1]
        area -= ring[j][0] * ring[i][1]
    return area / 2.0
