import csv
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List

from django.conf import settings


# Very small "BallTree-like" helper: precompute station lat/lon in radians
# and do radius queries with haversine distance. This keeps a simple
# spatial index without adding heavy dependencies.
_station_coords_rad: List[tuple] | None = None


@dataclass
class FuelStation:
    station_id: str
    name: str
    latitude: float
    longitude: float
    price_per_gallon: float


@lru_cache(maxsize=1)
def load_fuel_stations() -> List[FuelStation]:
    """
    Load fuel price data from the CSV file specified in settings.FUEL_PRICE_FILE.

    Expected CSV columns (header names are flexible but must contain at least):
    - id or station_id
    - name
    - lat or latitude
    - lon or lng or longitude
    - price or price_per_gallon
    """
    path = settings.FUEL_PRICE_FILE
    stations: list[FuelStation] = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try a few common header names
                station_id = (
                    row.get("station_id")
                    or row.get("id")
                    or row.get("StationId")
                    or ""
                )
                name = row.get("name") or row.get("Name") or "Unknown"
                lat_str = (
                    row.get("lat")
                    or row.get("latitude")
                    or row.get("Lat")
                    or row.get("Latitude")
                )
                lon_str = (
                    row.get("lon")
                    or row.get("lng")
                    or row.get("longitude")
                    or row.get("Lon")
                    or row.get("Longitude")
                )
                price_str = (
                    row.get("price")
                    or row.get("price_per_gallon")
                    or row.get("Price")
                )
                if not (lat_str and lon_str and price_str):
                    continue
                try:
                    stations.append(
                        FuelStation(
                            station_id=str(station_id),
                            name=name,
                            latitude=float(lat_str),
                            longitude=float(lon_str),
                            price_per_gallon=float(price_str),
                        )
                    )
                except ValueError:
                    # Skip malformed rows
                    continue
    except FileNotFoundError:
        # In assignment environments where the file is missing, return empty list
        return []

    return stations


def iter_fuel_stations() -> Iterable[FuelStation]:
    return load_fuel_stations()


def _ensure_spatial_index() -> None:
    """Build the in-memory radians coordinate list for fast haversine checks."""
    global _station_coords_rad
    if _station_coords_rad is not None:
        return
    stations = load_fuel_stations()
    coords: List[tuple] = []
    for s in stations:
        coords.append((math.radians(s.latitude), math.radians(s.longitude)))
    _station_coords_rad = coords


def station_indices_within_radius(lat: float, lon: float, radius_miles: float) -> List[int]:
    """Return list of indices (into load_fuel_stations()) for stations within radius_miles of (lat, lon)."""
    _ensure_spatial_index()
    if _station_coords_rad is None:
        return []
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    R = 3958.8
    res: List[int] = []
    for i, (plat, plon) in enumerate(_station_coords_rad):
        dphi = plat - lat_r
        dlambda = plon - lon_r
        a = math.sin(dphi / 2) ** 2 + math.cos(lat_r) * math.cos(plat) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist = R * c
        if dist <= radius_miles:
            res.append(i)
    return res


def station_indices_near_route(route_geometry: list, max_off_route_miles: float) -> List[int]:
    """Return unique station indices that are within max_off_route_miles of any sampled point along the route.

    To keep queries reasonable, sample the route geometry (every Nth point) instead of querying every point.
    """
    _ensure_spatial_index()
    if _station_coords_rad is None:
        return []
    n = len(route_geometry)
    if n == 0:
        return []
    # choose sampling step so we do at most ~150 queries
    step = max(1, n // 150)
    idxs_set: set = set()
    for i in range(0, n, step):
        pt = route_geometry[i]
        found = station_indices_within_radius(pt.lat, pt.lng, max_off_route_miles)
        for fi in found:
            idxs_set.add(fi)
    return sorted(idxs_set)






