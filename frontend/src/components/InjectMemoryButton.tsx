import React, { useState } from "react";
import type { MemoryEntry, MemoryEntryInput } from "../types";
import { injectMemory } from "../api";
import { Zap, RefreshCw } from "lucide-react";

const PR_HISTORY: MemoryEntryInput[] = [
  {
    category: "Team Convention",
    contributor: "Arjun Mehta",
    file_path: null,
    module: "project-wide",
    pattern_tag: "mutable-default-arg",
    description: "Mutable default arguments (e.g. def f(x=[])) are banned project-wide. Established in PR #1 when Arjun Mehta used `def process(data=[])`. Use None and initialize inside the function body instead.",
  },
  {
    category: "Recurring Mistake",
    contributor: "Arjun Mehta",
    file_path: null,
    module: "routes",
    pattern_tag: "missing-try-except-async",
    description: "Arjun Mehta has a recurring pattern of omitting try/except blocks around await calls in async route handlers. Flagged in PR #2 by Priya Nair, acknowledged but not resolved. Escalated in PR #4: 'This is the second time — please add this to your checklist.'",
  },
  {
    category: "Architectural Decision",
    contributor: null,
    file_path: null,
    module: "database",
    pattern_tag: "repository-layer",
    description: "All database calls must go through the repository layer. Direct ORM queries (e.g. db.query(Model).filter(...)) are not permitted in route handler files. Established in PR #3.",
  },
  {
    category: "Approved Exception",
    contributor: "Danielle Osei",
    file_path: "auth/legacy.py",
    module: "auth",
    pattern_tag: "legacy-auth-direct-query",
    description: "The legacy auth module (auth/legacy.py) is approved to use direct ORM queries until the Q3 authentication refactor is complete. Exception granted in PR #3.",
  },
];

interface Props {
  onSuccess: (entries: MemoryEntry[]) => void;
  onLoadingChange: (loading: boolean) => void;
}

export default function InjectMemoryButton({ onSuccess, onLoadingChange }: Props) {
  const [loading, setLoading] = useState(false);
  const [failCount, setFailCount] = useState(0);

  const inject = async () => {
    setLoading(true);
    onLoadingChange(true);
    setFailCount(0);
    try {
      const result = await injectMemory(PR_HISTORY);
      if (result.failed > 0) {
        setFailCount(result.failed);
      }
      const entries: MemoryEntry[] = PR_HISTORY.map((e, i) => ({
        ...e,
        id: `injected-${i}`,
        created_at: new Date().toISOString(),
      }));
      onSuccess(entries);
    } catch {
      setFailCount(PR_HISTORY.length);
    } finally {
      setLoading(false);
      onLoadingChange(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={inject}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-bold rounded-lg transition-colors"
      >
        {loading ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
        {loading ? "Injecting PR History..." : "Inject Memory (PR #1–4)"}
      </button>
      {failCount > 0 && (
        <p className="text-xs text-red-400">
          {failCount} write(s) failed.{" "}
          <button onClick={inject} className="underline hover:text-red-300">Retry</button>
        </p>
      )}
    </div>
  );
}
