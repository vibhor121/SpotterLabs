## Django Route Planner API

This is a small Django 5 project that exposes an API to:

- **Compute a driving route** between two locations in the USA (using a free routing API).
- **Find cost‑effective fuel stops** along the route given a vehicle range of **500 miles**.
- **Compute total fuel cost** assuming the vehicle achieves **10 miles per gallon**.

The project is backend‑only; you can visualize the returned `geometry` on any map client (Leaflet, Mapbox, etc.).

### 1. Project layout

- **server/**
  - `manage.py`
  - `requirements.txt`
  - `routeplanner/`
    - `settings.py`
    - `urls.py`
    - `wsgi.py`
  - `routing/`
    - `apps.py`
    - `urls.py`
    - `views.py`
    - `serializers.py`
    - `fuel_data.py`
    - `routing_api.py`
    - `fuel_optimizer.py`
  - `data/`
    - `fuel_prices.csv` (you must place the provided fuel price file here)

### 2. Dependencies

Install dependencies inside a virtualenv **located inside the `server` folder**:

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Routing API configuration (OpenRouteService)

This project is configured to use **OpenRouteService** directions API:

- Base URL: `https://api.openrouteservice.org/v2/directions/driving-car`
- You must create a free API key on OpenRouteService and set it via environment variable:

```bash
export ROUTING_API_KEY="your_openrouteservice_key_here"
```

Optional environment variables (defaults shown):

```bash
export DJANGO_SECRET_KEY="dev-secret-key-change-me"
export DJANGO_DEBUG=1
export FUEL_PRICE_FILE="$(pwd)/data/fuel_prices.csv"
export VEHICLE_RANGE_MILES=500
export VEHICLE_MPG=10
```

### 4. Fuel prices file

Place the **provided fuel prices file** into:

- `server/data/fuel_prices.csv`

Expected columns (header names are flexible; the loader tries common variants):

- `station_id` or `id`
- `name`
- `lat` or `latitude`
- `lon` / `lng` / `longitude`
- `price` or `price_per_gallon`

The loader is in `routing/fuel_data.py` and caches the parsed stations in memory for fast reuse.

### 5. Running the server

Run Django migrations (only the default auth/contenttypes tables):

```bash
cd server
python manage.py migrate
```

Start the development server:

```bash
python manage.py runserver 8000
```

The API root for this assignment is:

- `POST http://127.0.0.1:8000/api/route-plan/`

### 6. API usage

**Request body (JSON):**

```json
{
  "start": { "lat": 37.7749, "lng": -122.4194 },
  "end":   { "lat": 34.0522, "lng": -118.2437 }
}
```

Both points must be within the USA. The API assumes coordinates are in WGS84 decimal degrees.

**Response body (JSON, example shape):**

```json
{
  "distance_miles": 382.5,
  "duration_seconds": 20934.1,
  "geometry": [
    { "lat": 37.7749, "lng": -122.4194 },
    { "lat": 37.7, "lng": -122.3 }
    // ...
  ],
  "fuel_stops": [
    {
      "station_id": "123",
      "name": "Example Fuel",
      "latitude": 36.1,
      "longitude": -121.9,
      "price_per_gallon": 3.59,
      "distance_along_route_miles": 180.3,
      "gallons_purchased": 25.0,
      "cost_usd": 89.75
    }
  ],
  "total_gallons": 38.25,
  "total_cost_usd": 135.10
}
```

- **`geometry`**: list of coordinates representing the route polyline (you can draw this on a map).
- **`fuel_stops`**: optimal/greedy fuel stops along the route, prioritizing cheaper stations within reach.
- **`total_gallons`** and **`total_cost_usd`**: total fuel consumption and money spent based on **10 mpg**.

### 7. Performance and API call minimization

- The app performs **one call** to the routing API (`routing_api.get_route`) per request.
- Fuel prices are loaded into memory **once** on first use and cached (`functools.lru_cache`).
- All optimization work (distance calculations, fuel planning) is done **locally** in Python.


