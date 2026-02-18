from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from django.conf import settings

from . import fuel_data
from .fuel_data import FuelStation
from .routing_api import RouteInfo, RoutePoint


@dataclass
class FuelStopPlan:
    station: FuelStation
    distance_along_route_miles: float
    gallons_purchased: float
    cost_usd: float


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3958.8  # Earth radius in miles
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _build_route_distances(route: RouteInfo) -> List[float]:
    """Return cumulative distances at each point along the route."""
    dists: List[float] = [0.0]
    total = 0.0
    pts = route.geometry
    for i in range(1, len(pts)):
        seg = _haversine_miles(
            pts[i - 1].lat,
            pts[i - 1].lng,
            pts[i].lat,
            pts[i].lng,
        )
        total += seg
        dists.append(total)
    return dists


def _project_station_onto_route(
    station: FuelStation, route: RouteInfo, cum_dists: List[float]
) -> Tuple[float, float]:
    """
    Project a station onto the route polyline.

    Returns (distance_along_route_miles, distance_off_route_miles).
    """
    pts = route.geometry
    best_along = 0.0
    best_off = float("inf")

    for i in range(1, len(pts)):
        a = pts[i - 1]
        b = pts[i]
        # Approximate by taking min distance to segment endpoints
        da = _haversine_miles(station.latitude, station.longitude, a.lat, a.lng)
        db = _haversine_miles(station.latitude, station.longitude, b.lat, b.lng)
        seg_best_off = min(da, db)
        if seg_best_off < best_off:
            best_off = seg_best_off
            # Use segment end as distance along route
            best_along = cum_dists[i]

    return best_along, best_off


def _stations_along_route(
    stations: Iterable[FuelStation],
    route: RouteInfo,
    max_off_route_miles: float = 10.0,
) -> List[Tuple[FuelStation, float]]:
    """
    Filter stations to those reasonably close to the route and annotate with
    distance along the route in miles.
    """
    cum = _build_route_distances(route)
    results: List[Tuple[FuelStation, float]] = []

    # Use the spatial index to get a small set of candidate station indices
    try:
        candidate_idxs = fuel_data.station_indices_near_route(route.geometry, max_off_route_miles)
    except Exception:
        # Fall back to full scan on error
        candidate_idxs = None

    stations_list = list(stations)
    if candidate_idxs is None:
        iter_range = range(len(stations_list))
    else:
        iter_range = candidate_idxs

    for i in iter_range:
        s = stations_list[i]
        along, off = _project_station_onto_route(s, route, cum)
        if off <= max_off_route_miles:
            results.append((s, along))

    results.sort(key=lambda x: x[1])
    return results


def compute_fuel_plan(
    stations: Iterable[FuelStation],
    route: RouteInfo,
    vehicle_range_miles: float | None = None,
    mpg: float | None = None,
) -> List[FuelStopPlan]:
    """
    Simple greedy fuel optimization:

    - Vehicle has max range (tank size) in miles.
    - Look ahead up to range from current position and pick the cheapest within reach.
    - Buy enough fuel to reach either the next cheaper station or as far as possible.
    """
    if vehicle_range_miles is None:
        vehicle_range_miles = float(settings.VEHICLE_RANGE_MILES)
    if mpg is None:
        mpg = float(settings.VEHICLE_MPG)

    route_distance = route.distance_miles
    candidates = _stations_along_route(stations, route)
    if not candidates:
        return []

    stops: List[FuelStopPlan] = []
    current_pos = 0.0  # miles along route
    fuel_in_tank_miles = vehicle_range_miles  # start with a full tank
    idx = 0

    while current_pos < route_distance:
        # Determine the furthest we can go from current position
        max_reach = current_pos + vehicle_range_miles
        if max_reach >= route_distance:
            # We can reach the destination; buy just enough if needed and finish
            distance_needed = max(0.0, route_distance - current_pos - fuel_in_tank_miles)
            if distance_needed > 1e-6:
                # Buy at the current station if we are at one; otherwise skip cost
                if stops:
                    current_station = stops[-1].station
                    gallons = distance_needed / mpg
                    cost = gallons * current_station.price_per_gallon
                    stops.append(
                        FuelStopPlan(
                            station=current_station,
                            distance_along_route_miles=current_pos,
                            gallons_purchased=gallons,
                            cost_usd=cost,
                        )
                    )
            break

        # Find all candidate stations within reach ahead of us
        reachable: List[Tuple[FuelStation, float]] = []
        while idx < len(candidates) and candidates[idx][1] <= max_reach:
            if candidates[idx][1] >= current_pos:
                reachable.append(candidates[idx])
            idx += 1

        if not reachable:
            # No stations within reach; cannot complete route with given range
            break

        # Choose the cheapest station among reachable ones
        cheapest_station, cheapest_dist = min(
            reachable, key=lambda x: x[0].price_per_gallon
        )

        # Move to that station
        distance_to_station = max(0.0, cheapest_dist - current_pos)
        fuel_in_tank_miles -= distance_to_station
        current_pos = cheapest_dist

        # Decide how much to fill at this station:
        # look ahead for any cheaper station within full range
        max_from_here = current_pos + vehicle_range_miles
        cheaper_within_range = [
            (s, d)
            for (s, d) in candidates
            if current_pos < d <= max_from_here and s.price_per_gallon < cheapest_station.price_per_gallon
        ]
        if cheaper_within_range:
            # Only buy enough to reach the next cheaper station
            next_cheaper_station, next_cheaper_dist = min(
                cheaper_within_range, key=lambda x: x[1]
            )
            distance_needed = max(0.0, next_cheaper_dist - current_pos)
        else:
            # No cheaper station ahead within range; fill the tank
            distance_needed = vehicle_range_miles

        # Ensure we don't exceed what is needed to finish the route
        distance_needed = min(distance_needed, route_distance - current_pos)

        # Add missing fuel
        additional_needed = max(0.0, distance_needed - fuel_in_tank_miles)
        if additional_needed <= 1e-6:
            continue

        gallons = additional_needed / mpg
        cost = gallons * cheapest_station.price_per_gallon
        fuel_in_tank_miles += additional_needed

        stops.append(
            FuelStopPlan(
                station=cheapest_station,
                distance_along_route_miles=current_pos,
                gallons_purchased=gallons,
                cost_usd=cost,
            )
        )

    return stops




