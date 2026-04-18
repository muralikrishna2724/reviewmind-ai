import axios from "axios";
import type {
  ReviewResponse, InjectResponse, MemoryEntryInput,
  Project, ProjectFile, ReviewSummary,
} from "./types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "",
  headers: { "Content-Type": "application/json" },
});

// ── Review ────────────────────────────────────────────────────────────────────

export async function submitReview(
  code: string,
  contributor: string,
  options?: {
    filePath?: string;
    projectId?: string;
    fileId?: string;
    forceMemoryMode?: "with" | "without";
  }
): Promise<ReviewResponse> {
  const { data } = await api.post<ReviewResponse>("/review", {
    code,
    contributor,
    file_path: options?.filePath ?? null,
    project_id: options?.projectId ?? null,
    file_id: options?.fileId ?? null,
    force_memory_mode: options?.forceMemoryMode ?? null,
  });
  return data;
}

export async function injectMemory(entries: MemoryEntryInput[]): Promise<InjectResponse> {
  const { data } = await api.post<InjectResponse>("/inject-memory", { entries });
  return data;
}

export async function fetchMemory(): Promise<MemoryEntryInput[]> {
  const { data } = await api.get<{ entries: MemoryEntryInput[] }>("/memory");
  return Array.isArray(data?.entries) ? data.entries : [];
}

// ── Projects ──────────────────────────────────────────────────────────────────

export async function createProject(payload: {
  source_type: string;
  git_url?: string;
  branch?: string;
  name?: string;
}): Promise<Project> {
  const { data } = await api.post<Project>("/projects/create", payload);
  return data;
}

export async function listProjects(): Promise<Project[]> {
  const { data } = await api.get("/projects");
  // Handle both array response and wrapped { projects: [...] } response
  return Array.isArray(data) ? data : (data?.projects ?? []);
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/projects/${id}`);
}

// ── Files ─────────────────────────────────────────────────────────────────────

export async function listFiles(projectId: string): Promise<ProjectFile[]> {
  const { data } = await api.get<ProjectFile[]>(`/projects/${projectId}/files`);
  return data;
}

export async function getFileContent(projectId: string, fileId: string): Promise<string> {
  const { data } = await api.get<{ content: string }>(`/projects/${projectId}/files/${fileId}/content`);
  return data.content;
}

// ── Reviews ───────────────────────────────────────────────────────────────────

export async function listReviews(projectId: string): Promise<ReviewSummary[]> {
  const { data } = await api.get<{ reviews: ReviewSummary[] }>(`/projects/${projectId}/reviews`);
  return data.reviews;
}

export async function getReview(reviewId: string): Promise<ReviewResponse & { code_snapshot: string }> {
  const { data } = await api.get(`/reviews/${reviewId}`);
  return data;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export async function getAnalytics(projectId: string) {
  const { data } = await api.get(`/projects/${projectId}/analytics`);
  return data;
}

// ── PR Injection ──────────────────────────────────────────────────────────────

export async function injectPRs(
  projectId: string,
  limit: number = 30,
): Promise<{ fetched: number; written: number; failed: number; bank_id: string; errors: string[] }> {
  const { data } = await api.post(`/projects/${projectId}/inject-prs`, { limit });
  return data;
}
