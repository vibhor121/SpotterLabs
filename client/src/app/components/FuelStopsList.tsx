import { FuelStop } from "../types";

interface FuelStopsListProps {
  stops: FuelStop[];
}

export default function FuelStopsList({ stops }: FuelStopsListProps) {
  if (stops.length === 0) {
    return (
      <div>
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
          Fuel Stops
        </h2>
        <p className="text-sm text-gray-500 italic">No fuel stops needed.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
        Fuel Stops ({stops.length})
      </h2>
      <div className="flex flex-col gap-2 overflow-y-auto max-h-80 pr-1">
        {stops.map((stop, idx) => (
          <div
            key={stop.station_id}
            className="bg-gray-700 rounded-lg p-3 border border-gray-600"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-bold text-green-400">
                Stop {idx + 1}
              </span>
              <span className="text-xs text-gray-400">
                Mile {stop.distance_along_route_miles.toFixed(0)}
              </span>
            </div>
            <p className="text-sm font-semibold text-white truncate">
              {stop.name}
            </p>
            <div className="mt-2 grid grid-cols-3 gap-1 text-xs">
              <div className="text-center">
                <div className="text-gray-400">$/gal</div>
                <div className="font-semibold text-white">
                  ${stop.price_per_gallon.toFixed(3)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Gallons</div>
                <div className="font-semibold text-white">
                  {stop.gallons_purchased.toFixed(1)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Cost</div>
                <div className="font-semibold text-green-400">
                  ${stop.cost_usd.toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
