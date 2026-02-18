from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import requests
from django.conf import settings


@dataclass
class RoutePoint:
    lat: float
    lng: float


@dataclass
class RouteInfo:
    distance_miles: float
    duration_seconds: float
    geometry: List[RoutePoint]


class RoutingAPIError(Exception):
    pass


def _meters_to_miles(meters: float) -> float:
    return meters / 1609.344


def _decode_polyline(encoded: str) -> List[Tuple[float, float]]:
    """
    Decode a polyline string into a list of (lon, lat) coordinate tuples.
    Implements Google's polyline encoding algorithm.
    """
    coords = []
    index = 0
    lat = 0
    lng = 0
    
    while index < len(encoded):
        # Decode latitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat
        
        # Decode longitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng
        
        coords.append((lng / 1e5, lat / 1e5))
    
    return coords


def get_route(start: Tuple[float, float], end: Tuple[float, float]) -> RouteInfo:
    """
    Call OpenRouteService (or compatible) directions API once to retrieve the route.

    start/end are (lat, lng).
    """
    if not settings.ROUTING_API_KEY:
        raise RoutingAPIError(
            "ROUTING_API_KEY is not configured. Set it in environment variables."
        )

    base_url = settings.ROUTING_API_BASE_URL

    # OpenRouteService expects [lon, lat]
    body = {
        "coordinates": [
            [start[1], start[0]],
            [end[1], end[0]],
        ],
    }
    headers = {"Authorization": settings.ROUTING_API_KEY, "Content-Type": "application/json"}

    try:
        response = requests.post(base_url, json=body, headers=headers, timeout=10)
    except requests.RequestException as exc:
        raise RoutingAPIError(f"Error calling routing API: {exc}") from exc

    if response.status_code != 200:
        raise RoutingAPIError(
            f"Routing API returned {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    try:
        # OpenRouteService returns routes array (not features)
        route = data["routes"][0]
        summary = route["summary"]
        distance_meters = summary["distance"]
        duration_seconds = summary["duration"]
        
        # Geometry can be encoded polyline (string) or coordinates array
        geometry_data = route.get("geometry")
        if isinstance(geometry_data, str):
            # Decode polyline
            coords = _decode_polyline(geometry_data)
        else:
            # Already coordinates array
            coords = geometry_data if geometry_data else []
    except (KeyError, IndexError, TypeError) as exc:
        raise RoutingAPIError(f"Unexpected routing API response structure: {exc}") from exc

    geometry = [RoutePoint(lat=lat, lng=lon) for lon, lat in coords]

    return RouteInfo(
        distance_miles=_meters_to_miles(distance_meters),
        duration_seconds=float(duration_seconds),
        geometry=geometry,
    )


