from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


MEMORY_CATEGORIES = Literal[
    "Team Convention",
    "Recurring Mistake",
    "Architectural Decision",
    "Approved Exception",
    "Positive Pattern",
]


class ReviewRequest(BaseModel):
    code: str
    contributor: str
    file_path: str | None = None


class MemoryEntryInput(BaseModel):
    category: MEMORY_CATEGORIES
    contributor: str | None = None
    file_path: str | None = None
    module: str | None = None
    pattern_tag: str | None = None
    description: str


class MemoryEntry(MemoryEntryInput):
    id: str
    created_at: str


class ReviewOutput(BaseModel):
    critical_issues: list[str]
    convention_violations: list[str]
    contributor_patterns: list[str]
    positive_signals: list[str]
    summary: str  # exactly 2 sentences
    error: str | None = None  # set when LLM failed


class ReviewResponse(BaseModel):
    review: ReviewOutput
    memory_mode: Literal["with", "without"]
    recalled_entries: list[MemoryEntry]


class InjectRequest(BaseModel):
    entries: list[MemoryEntryInput]


class InjectResponse(BaseModel):
    written: int
    failed: int
    errors: list[str]
