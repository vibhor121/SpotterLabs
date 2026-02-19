import { LatLng, RoutePlanResponse } from "../types";

export async function geocodeAddress(address: string): Promise<LatLng> {
  const params = new URLSearchParams({
    q: address,
    format: "json",
    limit: "1",
    countrycodes: "us",
  });

  const res = await fetch(
    `https://nominatim.openstreetmap.org/search?${params}`,
    {
      headers: {
        "Accept-Language": "en",
        "User-Agent": "RoutePlannerApp/1.0",
      },
    }
  );

  if (!res.ok) {
    throw new Error(`Geocoding request failed: ${res.status}`);
  }

  const data = await res.json();

  if (!data || data.length === 0) {
    throw new Error(`Could not find location: "${address}"`);
  }

  return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
}

export async function fetchRoutePlan(
  start: LatLng,
  end: LatLng
): Promise<RoutePlanResponse> {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const res = await fetch(`${baseUrl}/api/route-plan/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      start: { lat: start.lat, lng: start.lng },
      end:   { lat: end.lat,   lng: end.lng   },
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Route plan request failed (${res.status}): ${text}`);
  }

  return res.json() as Promise<RoutePlanResponse>;
}
