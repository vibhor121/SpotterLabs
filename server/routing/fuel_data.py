import csv
import logging
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# US Cities lat/lon lookup (loaded once from simplemaps us_cities.csv)
# ---------------------------------------------------------------------------

_city_coords: Optional[Dict[Tuple[str, str], Tuple[float, float]]] = None

_CITIES_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "us_cities.csv")


def _load_city_coords() -> Dict[Tuple[str, str], Tuple[float, float]]:
    """Load simplemaps US cities CSV into a (city_lower, state_abbr) → (lat, lon) dict."""
    global _city_coords
    if _city_coords is not None:
        return _city_coords

    lookup: Dict[Tuple[str, str], Tuple[float, float]] = {}
    csv_path = os.path.normpath(_CITIES_CSV)
    if not os.path.exists(csv_path):
        logger.warning(
            "us_cities.csv not found at %s. "
            "Run: python manage.py download_city_data",
            csv_path,
        )
        _city_coords = lookup
        return lookup

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Support simplemaps format (city, state_id, lat, lng)
                # and kelvins format (CITY, STATE_CODE, LATITUDE, LONGITUDE)
                city = (
                    row.get("city") or row.get("City") or row.get("CITY") or ""
                ).strip()
                state = (
                    row.get("state_id")
                    or row.get("STATE_CODE")
                    or row.get("state")
                    or row.get("State")
                    or ""
                ).strip()
                lat_str = (
                    row.get("lat") or row.get("Lat")
                    or row.get("latitude") or row.get("LATITUDE") or ""
                )
                lon_str = (
                    row.get("lng") or row.get("lon")
                    or row.get("longitude") or row.get("LONGITUDE") or ""
                )
                if not (city and state and lat_str and lon_str):
                    continue
                try:
                    lat = float(lat_str)
                    lon = float(lon_str)
                except ValueError:
                    continue
                key = (city.lower(), state.upper())
                # Keep first occurrence
                if key not in lookup:
                    lookup[key] = (lat, lon)
    except Exception as exc:
        logger.error("Failed to load us_cities.csv: %s", exc)

    _city_coords = lookup
    logger.info("Loaded %d city coordinates from us_cities.csv", len(lookup))
    return lookup


def _city_latlon(city: str, state: str) -> Optional[Tuple[float, float]]:
    lookup = _load_city_coords()
    return lookup.get((city.lower(), state.upper()))


# ---------------------------------------------------------------------------
# Fuel station loader
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_fuel_stations() -> List[FuelStation]:
    """
    Load fuel price data from the CSV file specified in settings.FUEL_PRICE_FILE.

    Supports the OPIS truckstop CSV format:
        OPIS Truckstop ID | Truckstop Name | Address | City | State | Rack ID | Retail Price

    Also accepts generic CSVs with headers like:
        id/station_id, name, lat/latitude, lon/lng/longitude, price/price_per_gallon
    """
    path = settings.FUEL_PRICE_FILE
    stations: list[FuelStation] = []
    skipped = 0
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Station ID
                station_id = (
                    row.get("OPIS Truckstop ID")
                    or row.get("station_id")
                    or row.get("id")
                    or row.get("StationId")
                    or ""
                )
                # Name
                name = (
                    row.get("Truckstop Name")
                    or row.get("name")
                    or row.get("Name")
                    or "Unknown"
                )
                # Price
                price_str = (
                    row.get("Retail Price")
                    or row.get("price")
                    or row.get("price_per_gallon")
                    or row.get("Price")
                )
                if not price_str:
                    skipped += 1
                    continue

                # Lat/lon — try direct columns first, then city/state lookup
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

                lat: Optional[float] = None
                lon: Optional[float] = None

                if lat_str and lon_str:
                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                    except ValueError:
                        pass

                if lat is None or lon is None:
                    # Fall back to city/state geocoding via bundled lookup
                    city = (row.get("City") or row.get("city") or "").strip()
                    state = (row.get("State") or row.get("state") or "").strip()
                    if city and state:
                        coords = _city_latlon(city, state)
                        if coords:
                            lat, lon = coords
                        else:
                            logger.debug("No coords for city=%s state=%s", city, state)
                            skipped += 1
                            continue
                    else:
                        skipped += 1
                        continue

                try:
                    price = float(price_str)
                except ValueError:
                    skipped += 1
                    continue

                stations.append(
                    FuelStation(
                        station_id=str(station_id),
                        name=str(name),
                        latitude=lat,
                        longitude=lon,
                        price_per_gallon=price,
                    )
                )
    except FileNotFoundError:
        logger.warning("Fuel price file not found: %s", path)
        return []

    if skipped:
        logger.warning("Skipped %d rows from fuel CSV (missing price or coordinates)", skipped)
    logger.info("Loaded %d fuel stations", len(stations))
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
