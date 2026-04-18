import React, { useState, useEffect, useCallback } from "react";
import type { Project, ProjectFile, MemoryEntry, ReviewResponse, ReviewSummary } from "./types";
import {
  submitReview, injectMemory, listProjects, deleteProject,
  listFiles, getFileContent, listReviews,
} from "./api";
import Sidebar from "./components/Sidebar";
import NewProjectModal from "./components/NewProjectModal";
import FileExplorer from "./components/FileExplorer";
import CodeInputArea from "./components/CodeInputArea";
import ReviewOutputPanel from "./components/ReviewOutputPanel";
import MemoryPanel from "./components/MemoryPanel";
import ComparisonView from "./components/ComparisonView";
import { InjectMemoryButton } from "./components/InjectMemoryButton";
import { Columns2, Play, Loader2, AlertCircle } from "lucide-react";

const DEFAULT_CODE = `async def get_user_orders(user_id: int, filters=[]):
    result = await db.query(Order).filter(Order.user_id == user_id).all()
    return result`;

const DEFAULT_CONTRIBUTOR = "Arjun Mehta";

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(null);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [recentReviews, setRecentReviews] = useState<ReviewSummary[]>([]);
  const [selectedFile, setSelectedFile] = useState<ProjectFile | null>(null);
  const [code, setCode] = useState(DEFAULT_CODE);
  const [contributor, setContributor] = useState(DEFAULT_CONTRIBUTOR);
  const [memoryEntries, setMemoryEntries] = useState<MemoryEntry[]>([]);
  const [memoryLoading, setMemoryLoading] = useState(false);
  const [reviewResult, setReviewResult] = useState<ReviewResponse | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState<string | undefined>();
  const [comparisonMode, setComparisonMode] = useState(false);
  const [withoutReview, setWithoutReview] = useState<ReviewResponse | null>(null);
  const [withReview, setWithReview] = useState<ReviewResponse | null>(null);
  const [showNewProject, setShowNewProject] = useState(false);

  // Load projects on mount — gracefully handle backend being unavailable
  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((err) => {
        console.warn("Backend unavailable:", err?.message ?? err);
        // App still renders — just no projects loaded
      });
  }, []);

  // Load files + reviews when project changes
  useEffect(() => {
    if (!currentProjectId) return;
    listFiles(currentProjectId).then(setFiles).catch(() => {});
    listReviews(currentProjectId).then(setRecentReviews).catch(() => {});
  }, [currentProjectId]);

  // Load file content when file selected
  useEffect(() => {
    if (!selectedFile || !currentProjectId) return;
    getFileContent(currentProjectId, selectedFile.id)
      .then(setCode)
      .catch(() => {});
  }, [selectedFile, currentProjectId]);

  const handleReview = useCallback(async () => {
    setReviewLoading(true);
    setReviewError(undefined);
    try {
      const result = await submitReview(code, contributor, {
        projectId: currentProjectId ?? undefined,
        fileId: selectedFile?.id,
        filePath: selectedFile?.path,
      });
      setReviewResult(result);
      // Refresh recent reviews
      if (currentProjectId) {
        listReviews(currentProjectId).then(setRecentReviews).catch(() => {});
      }
    } catch (e: unknown) {
      setReviewError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setReviewLoading(false);
    }
  }, [code, contributor, currentProjectId, selectedFile]);

  const handleComparison = useCallback(async () => {
    setReviewLoading(true);
    setReviewError(undefined);
    setWithoutReview(null);
    setWithReview(null);
    try {
      const [r1, r2] = await Promise.all([
        submitReview(code, contributor, {
          projectId: currentProjectId ?? undefined,
          forceMemoryMode: "without",
        }),
        submitReview(code, contributor, {
          projectId: currentProjectId ?? undefined,
          forceMemoryMode: "with",
        }),
      ]);
      setWithoutReview(r1);
      setWithReview(r2);
    } catch (e: unknown) {
      setReviewError(e instanceof Error ? e.message : "Comparison failed");
    } finally {
      setReviewLoading(false);
    }
  }, [code, contributor, currentProjectId]);

  const handleDeleteProject = async (id: string) => {
    await deleteProject(id).catch(() => {});
    setProjects(ps => ps.filter(p => p.id !== id));
    if (currentProjectId === id) {
      setCurrentProjectId(null);
      setFiles([]);
      setRecentReviews([]);
    }
  };

  const handleProjectCreated = (project: Project) => {
    setProjects(ps => [project, ...ps]);
    setCurrentProjectId(project.id);
  };

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        projects={projects}
        currentProjectId={currentProjectId}
        recentReviews={recentReviews}
        onProjectChange={id => { setCurrentProjectId(id); setSelectedFile(null); setReviewResult(null); }}
        onNewProject={() => setShowNewProject(true)}
        onInjectMemory={() => {}}
        onDeleteProject={handleDeleteProject}
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <div className="border-b border-gray-800 px-6 py-3 flex items-center justify-between shrink-0">
          <div>
            <h1 className="text-sm font-bold text-white">
              {projects.find(p => p.id === currentProjectId)?.name ?? "ReviewMind AI"}
            </h1>
            <p className="text-xs text-gray-500">Persistent memory-powered code review</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={comparisonMode}
                onChange={e => { setComparisonMode(e.target.checked); setWithoutReview(null); setWithReview(null); }}
                className="rounded"
              />
              <Columns2 size={13} />
              Comparison Mode
            </label>
            <input
              value={contributor}
              onChange={e => setContributor(e.target.value)}
              placeholder="Contributor"
              className="px-3 py-1.5 text-xs bg-gray-800 border border-gray-700 rounded-lg text-gray-200 outline-none w-36"
            />
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 flex overflow-hidden">
          {/* File explorer (only if project has files) */}
          {files.length > 0 && (
            <div className="w-52 border-r border-gray-800 p-3 overflow-y-auto shrink-0">
              <FileExplorer
                files={files}
                onFileSelect={setSelectedFile}
                selectedFileId={selectedFile?.id}
              />
            </div>
          )}

          {/* Center: code + review */}
          <div className="flex-1 flex flex-col overflow-hidden p-4 gap-4">
            {comparisonMode ? (
              <>
                <CodeInputArea value={code} onChange={setCode} />
                <button
                  onClick={handleComparison}
                  disabled={reviewLoading}
                  className="flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-white text-sm font-bold rounded-lg transition-colors"
                >
                  {reviewLoading ? <><Loader2 size={14} className="animate-spin" /> Running...</> : <><Columns2 size={14} /> Run Side-by-Side Comparison</>}
                </button>
                {reviewError && (
                  <div className="flex items-center gap-2 text-xs text-red-400">
                    <AlertCircle size={13} /> {reviewError}
                  </div>
                )}
                {withoutReview && withReview && (
                  <div className="flex-1 overflow-y-auto">
                    <ComparisonView withoutReview={withoutReview.review} withReview={withReview.review} />
                  </div>
                )}
              </>
            ) : (
              <>
                <CodeInputArea value={code} onChange={setCode} />
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleReview}
                    disabled={reviewLoading}
                    className="flex items-center gap-2 px-5 py-2.5 bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white text-sm font-bold rounded-lg transition-colors"
                  >
                    {reviewLoading ? <><Loader2 size={14} className="animate-spin" /> Reviewing...</> : <><Play size={14} /> Review Code</>}
                  </button>
                  <InjectMemoryButton
                    onSuccess={setMemoryEntries}
                    onLoadingChange={setMemoryLoading}
                  />
                </div>
                {reviewError && (
                  <div className="flex items-center gap-2 text-xs text-red-400">
                    <AlertCircle size={13} /> {reviewError}
                  </div>
                )}
                {(reviewResult || reviewLoading) && (
                  <div className="flex-1 overflow-y-auto">
                    <ReviewOutputPanel
                      review={reviewResult?.review ?? null}
                      mode={reviewResult?.memory_mode ?? "without"}
                      loading={reviewLoading}
                      error={reviewError}
                    />
                  </div>
                )}
              </>
            )}
          </div>

          {/* Right: memory panel */}
          <div className="w-72 border-l border-gray-800 p-3 overflow-y-auto shrink-0">
            <MemoryPanel entries={memoryEntries} loading={memoryLoading} />
          </div>
        </div>
      </div>

      {showNewProject && (
        <NewProjectModal
          onClose={() => setShowNewProject(false)}
          onSuccess={handleProjectCreated}
        />
      )}
    </div>
  );
}
