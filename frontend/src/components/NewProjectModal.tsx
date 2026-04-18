import React, { useState } from "react";
import { createProject } from "../api";
import type { Project } from "../types";
import { X, GitBranch, Loader2 } from "lucide-react";

interface Props {
  onClose: () => void;
  onSuccess: (project: Project) => void;
}

export default function NewProjectModal({ onClose, onSuccess }: Props) {
  const [tab, setTab] = useState<"paste" | "git">("paste");
  const [name, setName] = useState("");
  const [gitUrl, setGitUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    setLoading(true);
    setError("");
    try {
      const project = await createProject({
        source_type: tab,
        name: name || undefined,
        git_url: tab === "git" ? gitUrl : undefined,
        branch: tab === "git" ? branch : undefined,
      });
      onSuccess(project);
      onClose();
    } catch (e: unknown) {
      // Extract the actual detail from the backend response if available
      const axiosErr = e as { response?: { data?: { detail?: string } }; message?: string };
      const detail = axiosErr?.response?.data?.detail;
      setError(detail ?? (e instanceof Error ? e.message : "Failed to create project"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-white">New Project</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 bg-gray-800 rounded-lg p-1">
          {(["paste", "git"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors
                ${tab === t ? "bg-gray-700 text-white" : "text-gray-400 hover:text-gray-200"}`}
            >
              {t === "paste" ? "Paste Code" : "Git Repository"}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Project Name</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={tab === "git" ? "Auto-detected from URL" : "My Project"}
              className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 outline-none focus:border-blue-500"
            />
          </div>

          {tab === "git" && (
            <>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Repository URL</label>
                <input
                  value={gitUrl}
                  onChange={e => setGitUrl(e.target.value)}
                  placeholder="https://github.com/username/repo"
                  className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Branch</label>
                <div className="relative">
                  <GitBranch size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input
                    value={branch}
                    onChange={e => setBranch(e.target.value)}
                    placeholder="main"
                    className="w-full pl-8 pr-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 outline-none focus:border-blue-500"
                  />
                </div>
              </div>
            </>
          )}

          {error && <p className="text-xs text-red-400">{error}</p>}

          <button
            onClick={handleCreate}
            disabled={loading || (tab === "git" && !gitUrl)}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-white text-sm font-bold rounded-lg transition-colors"
          >
            {loading ? <><Loader2 size={14} className="animate-spin" /> Creating...</> : "Create Project"}
          </button>
        </div>
      </div>
    </div>
  );
}
