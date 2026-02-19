"use client";

import { useState } from "react";
import { geocodeAddress, fetchRoutePlan } from "./api/routePlan";
import { RoutePlanResponse } from "./types";
import SearchForm from "./components/SearchForm";
import RouteMap from "./components/RouteMap";
import SummaryPanel from "./components/SummaryPanel";
import FuelStopsList from "./components/FuelStopsList";

export default function Home() {
  const [startInput, setStartInput] = useState("");
  const [endInput, setEndInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [routeData, setRouteData] = useState<RoutePlanResponse | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setRouteData(null);
    setIsLoading(true);

    try {
      const [startCoord, endCoord] = await Promise.all([
        geocodeAddress(startInput),
        geocodeAddress(endInput),
      ]);

      const data = await fetchRoutePlan(startCoord, endCoord);
      setRouteData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-80 flex-shrink-0 bg-gray-800 flex flex-col gap-5 p-5 overflow-y-auto z-10 shadow-xl">
        <div>
          <h1 className="text-xl font-bold text-white">Route Planner</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Optimized fuel stops across the USA
          </p>
        </div>

        <SearchForm
          startInput={startInput}
          endInput={endInput}
          isLoading={isLoading}
          onStartChange={setStartInput}
          onEndChange={setEndInput}
          onSubmit={handleSubmit}
        />

        {error && (
          <div className="rounded-lg bg-red-900/60 border border-red-700 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        {routeData && (
          <>
            <SummaryPanel data={routeData} />
            <FuelStopsList stops={routeData.fuel_stops} />
          </>
        )}
      </aside>

      {/* Map area */}
      <main className="flex-1 relative">
        <RouteMap routeData={routeData} />

        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-[1000]">
            <div className="flex flex-col items-center gap-3">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-400 border-t-transparent" />
              <span className="text-white font-medium text-sm">
                Planning your route…
              </span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
