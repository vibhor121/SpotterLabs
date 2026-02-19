"use client";

interface SearchFormProps {
  startInput: string;
  endInput: string;
  isLoading: boolean;
  onStartChange: (val: string) => void;
  onEndChange: (val: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export default function SearchForm({
  startInput,
  endInput,
  isLoading,
  onStartChange,
  onEndChange,
  onSubmit,
}: SearchFormProps) {
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <div>
        <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
          Start Location
        </label>
        <input
          type="text"
          value={startInput}
          onChange={(e) => onStartChange(e.target.value)}
          placeholder="e.g. Chicago, IL"
          required
          className="w-full rounded-lg bg-gray-700 border border-gray-600 px-3 py-2 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
          End Location
        </label>
        <input
          type="text"
          value={endInput}
          onChange={(e) => onEndChange(e.target.value)}
          placeholder="e.g. Dallas, TX"
          required
          className="w-full rounded-lg bg-gray-700 border border-gray-600 px-3 py-2 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="mt-1 w-full rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed px-4 py-2.5 text-sm font-semibold transition-colors"
      >
        {isLoading ? "Planning…" : "Plan Route"}
      </button>
    </form>
  );
}
