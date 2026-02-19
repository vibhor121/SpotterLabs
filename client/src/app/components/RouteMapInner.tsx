"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { RoutePlanResponse } from "../types";

// Fix broken default Leaflet marker icons in Webpack/Next.js
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const startEndIcon = L.divIcon({
  className: "",
  html: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="10" fill="#ef4444" stroke="white" stroke-width="2"/>
    <circle cx="12" cy="12" r="4" fill="white"/>
  </svg>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
  popupAnchor: [0, -14],
});

const fuelIcon = L.divIcon({
  className: "",
  html: `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
    <circle cx="14" cy="14" r="13" fill="#22c55e" stroke="white" stroke-width="2"/>
    <text x="14" y="19" font-size="14" text-anchor="middle" fill="white">⛽</text>
  </svg>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14],
  popupAnchor: [0, -16],
});

function FitBounds({ routeData }: { routeData: RoutePlanResponse }) {
  const map = useMap();

  useEffect(() => {
    if (routeData.geometry.length > 0) {
      const bounds = L.latLngBounds(
        routeData.geometry.map((p) => [p.lat, p.lng])
      );
      map.fitBounds(bounds, { padding: [40, 40] });
    }
  }, [routeData, map]);

  return null;
}

interface RouteMapInnerProps {
  routeData: RoutePlanResponse | null;
}

export default function RouteMapInner({ routeData }: RouteMapInnerProps) {
  const defaultCenter: [number, number] = [39.5, -98.35];

  return (
    <MapContainer
      center={defaultCenter}
      zoom={4}
      className="w-full h-full"
      style={{ background: "#1a1a2e" }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />

      {routeData && (
        <>
          <FitBounds routeData={routeData} />

          <Polyline
            positions={routeData.geometry.map((p) => [p.lat, p.lng])}
            pathOptions={{ color: "#3b82f6", weight: 4, opacity: 0.85 }}
          />

          {/* Start marker */}
          {routeData.geometry.length > 0 && (
            <Marker
              position={[
                routeData.geometry[0].lat,
                routeData.geometry[0].lng,
              ]}
              icon={startEndIcon}
            >
              <Popup>
                <strong>Start</strong>
              </Popup>
            </Marker>
          )}

          {/* End marker */}
          {routeData.geometry.length > 1 && (
            <Marker
              position={[
                routeData.geometry[routeData.geometry.length - 1].lat,
                routeData.geometry[routeData.geometry.length - 1].lng,
              ]}
              icon={startEndIcon}
            >
              <Popup>
                <strong>End</strong>
              </Popup>
            </Marker>
          )}

          {/* Fuel stop markers */}
          {routeData.fuel_stops.map((stop) => (
            <Marker
              key={stop.station_id}
              position={[stop.latitude, stop.longitude]}
              icon={fuelIcon}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-bold">{stop.name}</p>
                  <p>Mile {stop.distance_along_route_miles.toFixed(0)}</p>
                  <p>${stop.price_per_gallon.toFixed(3)}/gal</p>
                  <p>{stop.gallons_purchased.toFixed(1)} gal</p>
                  <p className="text-green-600 font-semibold">
                    Cost: ${stop.cost_usd.toFixed(2)}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}
        </>
      )}
    </MapContainer>
  );
}
