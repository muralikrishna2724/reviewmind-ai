import React, { useState } from "react";
import type { MemoryEntry, MemoryEntryInput } from "../types";
import { injectMemory, injectPRs } from "../api";
import { Zap, RefreshCw, GitPullRequest } from "lucide-react";

const PR_HISTORY: MemoryEntryInput[] = [
  {
    category: "Team Convention",
    contributor: "Arjun Mehta",
    file_path: null,
    module: "project-wide",
    pattern_tag: "mutable-default-arg",
    description: "Mutable default arguments (e.g. def f(x=[])) are banned project-wide. Use None and initialize inside the function body instead.",
  },
  {
    category: "Recurring Mistake",
    contributor: "Arjun Mehta",
    file_path: null,
    module: "routes",
    pattern_tag: "missing-try-except-async",
    description: "Arjun Mehta has a recurring pattern of omitting try/except blocks around await calls in async route handlers.",
  },
  {
    category: "Architectural Decision",
    contributor: null,
    file_path: null,
    module: "database",
    pattern_tag: "repository-layer",
    description: "All database calls must go through the repository layer. Direct ORM queries in route handler files are not permitted.",
  },
  {
    category: "Approved Exception",
    contributor: "Danielle Osei",
    file_path: "auth/legacy.py",
    module: "auth",
    pattern_tag: "legacy-auth-direct-query",
    description: "The legacy auth module (auth/legacy.py) is approved to use direct ORM queries until the Q3 authentication refactor is complete.",
  },
];

interface Props {
  onSuccess: (entries: MemoryEntry[]) => void;
  onLoadingChange: (loading: boolean) => void;
  projectId?: string | null;
}

export function InjectMemoryButton({ onSuccess, onLoadingChange, projectId }: Props) {
  const [loading, setLoading] = useState(false);
  const [failCount, setFailCount] = useState(0);
  const [failErrors, setFailErrors] = useState<string[]>([]);
  const [prLimit, setPrLimit] = useState(30);
  const [result, setResult] = useState<{ written: number; fetched: number } | null>(null);

  const injectFromGitHub = async () => {
    if (!projectId) return;
    setLoading(true);
    onLoadingChange(true);
    setFailCount(0);
    setFailErrors([]);
    setResult(null);
    try {
      const res = await injectPRs(projectId, prLimit);
      setResult({ written: res.written, fetched: res.fetched });
      if (res.failed > 0) {
        setFailCount(res.failed);
        setFailErrors(res.errors ?? []);
      }
      onSuccess([]);
    } catch (e: unknown) {
      setFailCount(prLimit);
      setFailErrors([e instanceof Error ? e.message : "Request failed"]);
    } finally {
      setLoading(false);
      onLoadingChange(false);
    }
  };

  const injectStatic = async () => {
    setLoading(true);
    onLoadingChange(true);
    setFailCount(0);
    setFailErrors([]);
    setResult(null);
    try {
      const res = await injectMemory(PR_HISTORY);
      if (res.failed > 0) {
        setFailCount(res.failed);
        setFailErrors(res.errors ?? []);
      }
      const entries: MemoryEntry[] = PR_HISTORY.map((e, i) => ({
        ...e,
        id: `injected-${i}`,
        created_at: new Date().toISOString(),
      }));
      onSuccess(entries);
    } catch (e: unknown) {
      setFailCount(PR_HISTORY.length);
      setFailErrors([e instanceof Error ? e.message : "Request failed"]);
    } finally {
      setLoading(false);
      onLoadingChange(false);
    }
  };

  if (projectId) {
    return (
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={1}
            max={100}
            value={prLimit}
            onChange={e => setPrLimit(Math.max(1, Math.min(100, Number(e.target.value))))}
            className="w-20 px-2 py-1.5 text-xs bg-gray-800 border border-gray-700 rounded-lg text-gray-200 outline-none focus:border-purple-500"
            title="Number of PRs to fetch (1-100)"
          />
          <button
            onClick={injectFromGitHub}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-purple-700 hover:bg-purple-600 disabled:bg-gray-700 disabled:text-gray-500 text-white text-xs font-bold rounded-lg transition-colors"
          >
            {loading
              ? <><RefreshCw size={13} className="animate-spin" /> Fetching PRs...</>
              : <><GitPullRequest size={13} /> Inject Last {prLimit} PRs</>}
          </button>
        </div>
        {result && (
          <p className="text-xs text-green-400">
            Fetched {result.fetched} PRs — {result.written} written to memory bank.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={injectStatic}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-bold rounded-lg transition-colors"
      >
        {loading
          ? <><RefreshCw size={14} className="animate-spin" /> Injecting...</>
          : <><Zap size={14} /> Inject Memory (PR #1-4)</>}
      </button>
      {failCount > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-xs text-red-400">
            {failCount} write(s) failed.{" "}
            <button onClick={injectStatic} className="underline hover:text-red-300">Retry</button>
          </p>
        </div>
      )}
    </div>
  );
}
