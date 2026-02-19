import { RoutePlanResponse } from "../types";

interface SummaryPanelProps {
  data: RoutePlanResponse;
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

interface StatCardProps {
  label: string;
  value: string;
}

function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="bg-gray-700 rounded-lg p-3 flex flex-col gap-1">
      <span className="text-xs text-gray-400 uppercase tracking-wide font-semibold">
        {label}
      </span>
      <span className="text-lg font-bold text-white">{value}</span>
    </div>
  );
}

export default function SummaryPanel({ data }: SummaryPanelProps) {
  return (
    <div>
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
        Trip Summary
      </h2>
      <div className="grid grid-cols-2 gap-2">
        <StatCard
          label="Distance"
          value={`${data.distance_miles.toFixed(0)} mi`}
        />
        <StatCard
          label="Duration"
          value={formatDuration(data.duration_seconds)}
        />
        <StatCard
          label="Total Cost"
          value={`$${data.total_cost_usd.toFixed(2)}`}
        />
        <StatCard
          label="Gallons"
          value={data.total_gallons.toFixed(1)}
        />
      </div>
    </div>
  );
}
