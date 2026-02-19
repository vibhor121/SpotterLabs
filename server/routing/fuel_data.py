import csv
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Tuple

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
def _load_city_coords() -> Dict[Tuple[str, str], Tuple[float, float]]:
    """
    Load (CITY_UPPER, STATE_CODE_UPPER) -> (lat, lng) from us_cities.csv.
    Used to geocode fuel stations that only have city/state, not coordinates.
    """
    path = getattr(settings, "US_CITIES_FILE", "")
    coords: Dict[Tuple[str, str], Tuple[float, float]] = {}
    if not path:
        return coords
    try:
        with open(path, newline="", encoding="utf-8") as f:
            # Skip leading blank lines so DictReader picks up the real header
            non_empty = (line for line in f if line.strip())
            reader = csv.DictReader(non_empty)
            for row in reader:
                state = (row.get("STATE_CODE") or "").strip().upper()
                city = (row.get("CITY") or "").strip().upper()
                lat_s = (row.get("LATITUDE") or "").strip()
                lon_s = (row.get("LONGITUDE") or "").strip()
                if not (city and state and lat_s and lon_s):
                    continue
                try:
                    coords[(city, state)] = (float(lat_s), float(lon_s))
                except ValueError:
                    continue
    except FileNotFoundError:
        pass
    return coords


@lru_cache(maxsize=1)
def load_fuel_stations() -> List[FuelStation]:
    """
    Load fuel price data from the CSV file specified in settings.FUEL_PRICE_FILE.

    Supports the actual assessment CSV format:
        OPIS Truckstop ID, Truckstop Name, Address, City, State, Rack ID, Retail Price

    Also supports generic formats with flexible column names.
    When lat/lng columns are absent, geocodes city+state via us_cities.csv.
    """
    path = settings.FUEL_PRICE_FILE
    city_coords = _load_city_coords()
    stations: list[FuelStation] = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Station ID — actual CSV uses "OPIS Truckstop ID"
                station_id = (
                    row.get("OPIS Truckstop ID")
                    or row.get("station_id")
                    or row.get("id")
                    or row.get("StationId")
                    or ""
                )
                # Name — actual CSV uses "Truckstop Name"
                name = (
                    row.get("Truckstop Name")
                    or row.get("name")
                    or row.get("Name")
                    or "Unknown"
                )
                # City and state for geocoding fallback
                city = (row.get("City") or "").strip().upper()
                state = (row.get("State") or "").strip().upper()

                # Try direct lat/lng columns first
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

                # Price — actual CSV uses "Retail Price"
                price_str = (
                    row.get("Retail Price")
                    or row.get("price")
                    or row.get("price_per_gallon")
                    or row.get("Price")
                )

                if not price_str:
                    continue

                # If no direct coordinates, look up by city+state
                if not (lat_str and lon_str) and city and state:
                    coord = city_coords.get((city, state))
                    if coord:
                        lat_str = str(coord[0])
                        lon_str = str(coord[1])

                if not (lat_str and lon_str):
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
                    continue
    except FileNotFoundError:
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
