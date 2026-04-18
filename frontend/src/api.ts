import axios from "axios";
import type { ReviewResponse, InjectResponse, MemoryEntryInput } from "./types";

const api = axios.create({
  baseURL: "",  // proxied via vite to http://localhost:8000
  headers: { "Content-Type": "application/json" },
});

export async function submitReview(
  code: string,
  contributor: string,
  filePath?: string
): Promise<ReviewResponse> {
  const { data } = await api.post<ReviewResponse>("/review", {
    code,
    contributor,
    file_path: filePath ?? null,
  });
  return data;
}

export async function injectMemory(
  entries: MemoryEntryInput[]
): Promise<InjectResponse> {
  const { data } = await api.post<InjectResponse>("/inject-memory", { entries });
  return data;
}
