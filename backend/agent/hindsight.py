"""Hindsight memory client using the official hindsight-client SDK.

Uses async methods (aretain / arecall) for all operations.
Never raises to the caller — errors are caught and converted to safe defaults.
"""
from __future__ import annotations

import logging
import os

from hindsight_client import Hindsight

from models.review import MemoryEntry, MemoryEntryInput

logger = logging.getLogger(__name__)

# Single bank for the ReviewMind AI demo
BANK_ID = "reviewmind-ai"


def _client() -> Hindsight:
    return Hindsight(
        base_url=os.environ.get("HINDSIGHT_INSTANCE_URL", "https://api.hindsight.vectorize.io"),
        api_key=os.environ["HINDSIGHT_API_KEY"],
    )


async def ensure_bank() -> None:
    """Create the memory bank if it doesn't exist yet."""
    client = _client()
    try:
        client.create_bank(
            bank_id=BANK_ID,
            name="ReviewMind AI — Crestline Software",
            background=(
                "Memory bank for the ReviewMind AI code review agent. "
                "Stores team conventions, recurring mistakes per contributor, "
                "architectural decisions, and approved exceptions for the Orion API project."
            ),
        )
        logger.info("Hindsight bank '%s' created.", BANK_ID)
    except Exception as exc:
        # Bank likely already exists — that's fine
        logger.debug("ensure_bank: %s", exc)
    finally:
        client.close()


async def write_memory(entry: MemoryEntryInput) -> bool:
    """Store a single memory entry in Hindsight.

    Returns True on success, False on any error (never raises).
    """
    client = _client()
    try:
        content = entry.description
        metadata: dict = {"category": entry.category}
        if entry.contributor:
            metadata["contributor"] = entry.contributor
        if entry.pattern_tag:
            metadata["pattern_tag"] = entry.pattern_tag
        if entry.module:
            metadata["module"] = entry.module
        if entry.file_path:
            metadata["file_path"] = entry.file_path

        context_parts = []
        if entry.category:
            context_parts.append(f"Category: {entry.category}")
        if entry.contributor:
            context_parts.append(f"Contributor: {entry.contributor}")
        if entry.pattern_tag:
            context_parts.append(f"Pattern: {entry.pattern_tag}")

        await client.aretain(
            bank_id=BANK_ID,
            content=content,
            context=", ".join(context_parts) if context_parts else None,
            metadata=metadata,
        )
        return True
    except Exception as exc:
        logger.error("Hindsight write_memory error: %s", exc)
        return False
    finally:
        await client.aclose()


async def list_memories() -> list[MemoryEntry]:
    """List all memories stored in the Hindsight bank.

    Returns a list of MemoryEntry records, or [] on any error (never raises).
    """
    client = _client()
    try:
        result = client.list_memories(bank_id=BANK_ID, limit=100)
        entries: list[MemoryEntry] = []
        for i, item in enumerate(result.items or []):
            try:
                meta: dict = {}
                if hasattr(item, "metadata") and item.metadata:
                    meta = item.metadata if isinstance(item.metadata, dict) else {}
                text = ""
                if hasattr(item, "content"):
                    text = item.content or ""
                elif hasattr(item, "text"):
                    text = item.text or ""
                else:
                    text = str(item)
                entry = MemoryEntry(
                    id=str(i),
                    created_at="",
                    category=meta.get("category", "Team Convention"),
                    contributor=meta.get("contributor"),
                    file_path=meta.get("file_path"),
                    module=meta.get("module"),
                    pattern_tag=meta.get("pattern_tag"),
                    description=text,
                )
                entries.append(entry)
            except Exception as parse_exc:
                logger.warning("Skipping unparseable memory item: %s", parse_exc)
        return entries
    except Exception as exc:
        logger.error("Hindsight list_memories error: %s", exc)
        return []
    finally:
        client.close()


async def query_memory(
    contributor: str | None = None,
    file_path: str | None = None,
    tags: list[str] | None = None,
) -> list[MemoryEntry]:
    """Retrieve relevant memory entries from Hindsight.

    Returns a list of MemoryEntry records, or [] on any error (never raises).
    """
    client = _client()
    try:
        # Build a natural-language query from available identifiers
        parts: list[str] = []
        if contributor:
            parts.append(f"contributor {contributor}")
        if file_path:
            parts.append(f"file {file_path}")
        if tags:
            parts.extend(tags[:3])
        query_text = " ".join(parts) if parts else "code review conventions and mistakes"

        result = await client.arecall(
            bank_id=BANK_ID,
            query=query_text,
            max_tokens=4096,
            budget="mid",
        )

        entries: list[MemoryEntry] = []
        for i, mem in enumerate(result.results or []):
            try:
                # Extract metadata if available
                meta: dict = {}
                if hasattr(mem, "metadata") and mem.metadata:
                    meta = mem.metadata if isinstance(mem.metadata, dict) else {}

                entry = MemoryEntry(
                    id=str(i),
                    created_at="",
                    category=meta.get("category", "Team Convention"),
                    contributor=meta.get("contributor"),
                    file_path=meta.get("file_path"),
                    module=meta.get("module"),
                    pattern_tag=meta.get("pattern_tag"),
                    description=mem.text if hasattr(mem, "text") else str(mem),
                )
                entries.append(entry)
            except Exception as parse_exc:
                logger.warning("Skipping unparseable memory: %s", parse_exc)

        return entries
    except Exception as exc:
        logger.error("Hindsight query_memory error: %s", exc)
        return []
    finally:
        await client.aclose()
