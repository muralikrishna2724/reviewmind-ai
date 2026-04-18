import axios from "axios";
import type { ReviewResponse, InjectResponse, MemoryEntryInput } from "./types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "",
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
