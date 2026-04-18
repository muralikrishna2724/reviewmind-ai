import React, { useEffect, useState } from "react";
import type { MemoryEntry } from "../types";
import { Database, Loader2, RefreshCw } from "lucide-react";
import { fetchMemory } from "../api";

const CATEGORY_COLORS: Record<string, string> = {
  "Team Convention": "bg-blue-900 text-blue-300 border-blue-700",
  "Recurring Mistake": "bg-red-900 text-red-300 border-red-700",
  "Architectural Decision": "bg-purple-900 text-purple-300 border-purple-700",
  "Approved Exception": "bg-yellow-900 text-yellow-300 border-yellow-700",
  "Positive Pattern": "bg-green-900 text-green-300 border-green-700",
};

interface Props {
  // injectedEntries are passed in after a manual inject action
  injectedEntries?: MemoryEntry[];
  loading?: boolean;
}

export default function MemoryPanel({ injectedEntries, loading: externalLoading }: Props) {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [fetching, setFetching] = useState(false);

  const load = async () => {
    setFetching(true);
    try {
      const data = await fetchMemory();
      setEntries(data as unknown as MemoryEntry[]);
    } catch {
      // backend unavailable — keep existing entries
    } finally {
      setFetching(false);
    }
  };

  // Fetch on mount
  useEffect(() => { load(); }, []);

  // When new entries are injected externally, merge them in and refresh
  useEffect(() => {
    if (injectedEntries && injectedEntries.length > 0) {
      load();
    }
  }, [injectedEntries]);

  const loading = externalLoading || fetching;
  const displayEntries = entries.length > 0 ? entries : (injectedEntries ?? []);

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <Database size={16} className="text-blue-400" />
        <h3 className="text-sm font-bold text-gray-200">Hindsight Memory</h3>
        <span className="ml-auto text-xs text-gray-500">{displayEntries.length} entries</span>
        <button
          onClick={load}
          disabled={fetching}
          className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
          title="Refresh memory"
        >
          <RefreshCw size={12} className={fetching ? "animate-spin" : ""} />
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-blue-400 text-sm py-4 justify-center">
          <Loader2 size={16} className="animate-spin" />
          <span>Loading memory...</span>
        </div>
      )}

      {!loading && displayEntries.length === 0 && (
        <div className="text-center py-6">
          <p className="text-gray-600 text-xs">No memory entries found</p>
          <p className="text-gray-700 text-xs mt-1">Use "Inject Memory" to load PR history</p>
        </div>
      )}

      {!loading && displayEntries.length > 0 && (
        <div className="space-y-2 overflow-y-auto flex-1">
          {displayEntries.map((entry, i) => (
            <div key={(entry as MemoryEntry).id || i} className="bg-gray-800 rounded p-2 border border-gray-700">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className={`text-xs px-2 py-0.5 rounded border font-medium ${CATEGORY_COLORS[entry.category] ?? "bg-gray-700 text-gray-300 border-gray-600"}`}>
                  {entry.category}
                </span>
                {entry.contributor && (
                  <span className="text-xs text-gray-400">@{entry.contributor}</span>
                )}
                {entry.pattern_tag && (
                  <span className="text-xs text-gray-500 font-mono">#{entry.pattern_tag}</span>
                )}
              </div>
              <p className="text-xs text-gray-300 leading-relaxed line-clamp-2">{entry.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
