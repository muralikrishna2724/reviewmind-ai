import React, { useState } from "react";
import type { Project, ReviewSummary } from "../types";
import { Brain, FolderOpen, Plus, Zap, Clock, Trash2, ChevronDown } from "lucide-react";

interface Props {
  projects: Project[];
  currentProjectId: string | null;
  recentReviews: ReviewSummary[];
  onProjectChange: (id: string) => void;
  onNewProject: () => void;
  onInjectMemory: () => void;
  onDeleteProject: (id: string) => void;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function Sidebar({
  projects, currentProjectId, recentReviews,
  onProjectChange, onNewProject, onInjectMemory, onDeleteProject,
}: Props) {
  const [search, setSearch] = useState("");
  const [showProjects, setShowProjects] = useState(true);
  const current = (projects ?? []).find(p => p.id === currentProjectId);
  const filtered = (projects ?? []).filter(p => p.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="w-60 bg-gray-900 border-r border-gray-800 flex flex-col h-screen shrink-0">
      {/* Logo */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Brain size={20} className="text-blue-400" />
          <span className="font-bold text-white text-sm">ReviewMind AI</span>
        </div>
        {current && (
          <div className="mt-2 flex items-center gap-1 text-xs text-gray-400">
            <FolderOpen size={12} />
            <span className="truncate">{current.name}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="p-3 space-y-1 border-b border-gray-800">
        <button
          onClick={onNewProject}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium bg-blue-700 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          <Plus size={13} /> New Project
        </button>
        <button
          onClick={onInjectMemory}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg transition-colors"
        >
          <Zap size={13} /> Inject Memory
        </button>
      </div>

      {/* Recent Reviews */}
      {recentReviews.length > 0 && (
        <div className="p-3 border-b border-gray-800">
          <div className="flex items-center gap-1 text-xs text-gray-500 font-semibold uppercase mb-2">
            <Clock size={11} /> Recent
          </div>
          <div className="space-y-1">
            {recentReviews.slice(0, 5).map(r => (
              <div key={r.id} className="px-2 py-1.5 rounded hover:bg-gray-800 cursor-pointer">
                <div className="text-xs text-gray-300 truncate">{r.file_path || "Code snippet"}</div>
                <div className="text-xs text-gray-600">{timeAgo(r.created_at)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Projects */}
      <div className="flex-1 overflow-y-auto p-3">
        <button
          onClick={() => setShowProjects(s => !s)}
          className="w-full flex items-center justify-between text-xs text-gray-500 font-semibold uppercase mb-2"
        >
          <span>Projects ({(projects ?? []).length})</span>
          <ChevronDown size={12} className={`transition-transform ${showProjects ? "" : "-rotate-90"}`} />
        </button>

        {showProjects && (
          <>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search..."
              className="w-full px-2 py-1.5 mb-2 text-xs bg-gray-800 border border-gray-700 rounded text-gray-200 placeholder-gray-600 outline-none"
            />
            <div className="space-y-0.5">
              {(filtered ?? []).map(p => (
                <div
                  key={p.id}
                  className={`group flex items-center justify-between px-2 py-2 rounded cursor-pointer transition-colors
                    ${p.id === currentProjectId ? "bg-blue-900/50 text-blue-300" : "hover:bg-gray-800 text-gray-300"}`}
                  onClick={() => onProjectChange(p.id)}
                >
                  <div className="min-w-0">
                    <div className="text-xs font-medium truncate">{p.name}</div>
                    <div className="text-xs text-gray-600">{p.file_count} files · {p.review_count} reviews</div>
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); onDeleteProject(p.id); }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-opacity"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-gray-800 text-xs text-gray-600 flex justify-between">
        <span>v2.0.0</span>
        <span>ReviewMind AI</span>
      </div>
    </div>
  );
}
