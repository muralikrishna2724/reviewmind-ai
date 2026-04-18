export type MemoryCategory =
  | "Team Convention"
  | "Recurring Mistake"
  | "Architectural Decision"
  | "Approved Exception"
  | "Positive Pattern";

export type MemoryMode = "with" | "without";

export interface MemoryEntryInput {
  category: MemoryCategory;
  contributor?: string | null;
  file_path?: string | null;
  module?: string | null;
  pattern_tag?: string | null;
  description: string;
}

export interface MemoryEntry extends MemoryEntryInput {
  id: string;
  created_at: string;
}

export interface ReviewOutput {
  critical_issues: string[];
  convention_violations: string[];
  contributor_patterns: string[];
  positive_signals: string[];
  summary: string;
  error?: string | null;
}

export interface ReviewResponse {
  review: ReviewOutput;
  memory_mode: MemoryMode;
  recalled_entries: MemoryEntry[];
  review_id?: string;
  processing_time_ms?: number;
}

export interface InjectResponse {
  written: number;
  failed: number;
  errors: string[];
}

export interface Project {
  id: string;
  name: string;
  source_type: string;
  source_url?: string | null;
  file_count: number;
  review_count: number;
  created_at: string;
}

export interface ProjectFile {
  id: string;
  path: string;
  name: string;
  size: number;
  type: string;
  reviewed: boolean;
}

export interface ReviewSummary {
  id: string;
  file_path: string | null;
  contributor: string | null;
  memory_mode: MemoryMode;
  summary: string | null;
  created_at: string;
}
