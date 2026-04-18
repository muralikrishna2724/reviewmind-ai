import React from "react";
import type { MemoryEntry } from "../types";
import { Database, Loader2 } from "lucide-react";

const CATEGORY_COLORS: Record<string, string> = {
  "Team Convention": "bg-blue-900 text-blue-300 border-blue-700",
  "Recurring Mistake": "bg-red-900 text-red-300 border-red-700",
  "Architectural Decision": "bg-purple-900 text-purple-300 border-purple-700",
  "Approved Exception": "bg-yellow-900 text-yellow-300 border-yellow-700",
  "Positive Pattern": "bg-green-900 text-green-300 border-green-700",
};

interface Props {
  entries: MemoryEntry[];
  loading: boolean;
}

export default function MemoryPanel({ entries, loading }: Props) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 h-full">
      <div className="flex items-center gap-2 mb-3">
        <Database size={16} className="text-blue-400" />
        <h3 className="text-sm font-bold text-gray-200">Hindsight Memory</h3>
        <span className="ml-auto text-xs text-gray-500">{entries.length} entries</span>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-blue-400 text-sm py-4 justify-center">
          <Loader2 size={16} className="animate-spin" />
          <span>Injecting memory...</span>
        </div>
      )}

      {!loading && entries.length === 0 && (
        <p className="text-gray-600 text-xs text-center py-4">No memory loaded</p>
      )}

      {!loading && entries.length > 0 && (
        <div className="space-y-2 overflow-y-auto max-h-80">
          {entries.map((entry, i) => (
            <div key={entry.id || i} className="bg-gray-800 rounded p-2 border border-gray-700">
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
