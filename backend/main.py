"""ReviewMind AI — FastAPI application entry point.

Routes:
  POST /review         — run the 7-stage review pipeline
  POST /inject-memory  — bulk-write synthetic PR history to Hindsight

Startup:
  Validates all required environment variables before accepting requests.
  Raises SystemExit if any are missing, logging each missing variable name.
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent import hindsight
from agent.workflow import run_review
from models.review import InjectRequest, InjectResponse, ReviewRequest, ReviewResponse

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = [
    "HINDSIGHT_API_KEY",
    "GROQ_API_KEY",
    "HINDSIGHT_INSTANCE_URL",
    "GROQ_MODEL",
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Validate required environment variables at startup."""
    missing = [var for var in _REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        for var in missing:
            logger.error("Missing required environment variable: %s", var)
        logger.error(
            "Startup failed. Missing variables: %s. "
            "Copy .env.example to .env and fill in your API keys.",
            ", ".join(missing),
        )
        sys.exit(1)
    logger.info("All required environment variables present. Starting ReviewMind AI.")
    await hindsight.ensure_bank()
    yield


app = FastAPI(
    title="ReviewMind AI",
    description="Persistent memory-powered code review agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/review", response_model=ReviewResponse)
async def review_code(request: ReviewRequest) -> ReviewResponse:
    """Run the full 7-stage CascadeFlow review pipeline."""
    return await run_review(request)


@app.post("/inject-memory", response_model=InjectResponse)
async def inject_memory(request: InjectRequest) -> InjectResponse:
    """Bulk-write memory entries to Hindsight (used for demo injection)."""
    written = 0
    failed = 0
    errors: list[str] = []

    for entry in request.entries:
        success = await hindsight.write_memory(entry)
        if success:
            written += 1
        else:
            failed += 1
            errors.append(f"Failed to write entry: {entry.description[:80]}")

    return InjectResponse(written=written, failed=failed, errors=errors)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
