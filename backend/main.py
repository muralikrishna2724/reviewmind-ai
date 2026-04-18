"""ReviewMind AI — FastAPI application (Production)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = ["HINDSIGHT_API_KEY", "GROQ_API_KEY", "HINDSIGHT_INSTANCE_URL", "GROQ_MODEL"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        for v in missing:
            logger.error("Missing env var: %s", v)
        sys.exit(1)
    logger.info("Starting ReviewMind AI (production mode)")
    from database import init_db
    await init_db()
    from agent import hindsight
    await hindsight.ensure_bank()
    yield


app = FastAPI(title="ReviewMind AI", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Dependency ────────────────────────────────────────────────────────────────

from database import get_db
from models.db_models import File, Project, PullRequest, Review
from models.review import (
    InjectRequest, InjectResponse, MemoryEntryInput,
    ReviewRequest, ReviewResponse,
)
from agent import hindsight
from agent.workflow import run_review
from services import git_service
from services import github_service


# ── Pydantic request/response schemas ────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    source_type: str = "paste"  # 'git', 'paste'
    git_url: Optional[str] = None
    branch: str = "main"
    name: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    source_type: str
    source_url: Optional[str]
    file_count: int
    review_count: int
    created_at: str


class ReviewRequestV2(ReviewRequest):
    project_id: Optional[str] = None
    file_id: Optional[str] = None
    force_memory_mode: Optional[str] = None  # 'with' | 'without' | None


class ReviewResponseV2(ReviewResponse):
    review_id: str
    processing_time_ms: int


# ── Helper ────────────────────────────────────────────────────────────────────

def _project_to_response(p: Project) -> ProjectResponse:
    return ProjectResponse(
        id=str(p.id),
        name=p.name,
        source_type=p.source_type,
        source_url=p.source_url,
        file_count=p.file_count or 0,
        review_count=p.review_count or 0,
        created_at=p.created_at.isoformat() if p.created_at else "",
    )


# ── Project endpoints ─────────────────────────────────────────────────────────

@app.post("/projects/create", response_model=ProjectResponse)
async def create_project(req: CreateProjectRequest, db: AsyncSession = Depends(get_db)):
    project_id = str(uuid.uuid4())
    name = req.name or "Untitled Project"
    storage_path = None
    file_count = 0

    if req.source_type == "git" and req.git_url:
        name = req.name or req.git_url.rstrip("/").split("/")[-1].replace(".git", "")
        try:
            result = await git_service.clone_repository(req.git_url, project_id, req.branch)
            storage_path = result["path"]
            files = git_service.parse_file_tree(Path(storage_path))
            file_count = len(files)
            for f in files:
                db.add(File(
                    project_id=project_id,
                    path=f["path"], name=f["name"],
                    size=f["size"], file_type=f["type"],
                ))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Git clone failed: {exc}")

    project = Project(
        id=project_id, name=name,
        source_type=req.source_type,
        source_url=req.git_url,
        branch=req.branch if req.source_type == "git" else None,
        storage_path=storage_path,
        file_count=file_count,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Fetch PRs from GitHub after project is saved (non-blocking — failures are logged, not raised)
    if req.source_type == "git" and req.git_url:
        try:
            prs = await asyncio.to_thread(github_service.fetch_pull_requests, req.git_url)
            for pr in prs:
                db.add(PullRequest(
                    project_id=project_id,
                    pr_number=pr["number"],
                    title=pr["title"],
                    state=pr["state"],
                    author=pr["author"],
                    branch=pr["branch"],
                    base_branch=pr["base_branch"],
                    body=pr["body"],
                    pr_created_at=pr["created_at"],
                    pr_updated_at=pr["updated_at"],
                    merged_at=pr["merged_at"],
                    url=pr["url"],
                    diff_url=pr["diff_url"],
                ))
            await db.commit()
            logger.info("Fetched %d PRs for project %s", len(prs), project_id)
        except Exception as exc:
            logger.warning("Could not fetch PRs for %s: %s", req.git_url, exc)

    return _project_to_response(project)


@app.get("/projects", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return [_project_to_response(p) for p in result.scalars().all()]


@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_response(p)


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(p)
    await db.commit()
    return {"deleted": True}


# ── File endpoints ────────────────────────────────────────────────────────────

@app.get("/projects/{project_id}/files")
async def list_files(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(File).where(File.project_id == project_id))
    files = result.scalars().all()
    return [{"id": str(f.id), "path": f.path, "name": f.name,
             "size": f.size, "type": f.file_type, "reviewed": f.reviewed}
            for f in files]


@app.get("/projects/{project_id}/prs")
async def list_pull_requests(project_id: str, db: AsyncSession = Depends(get_db)):
    """Return all pull requests fetched for this project."""
    result = await db.execute(
        select(PullRequest)
        .where(PullRequest.project_id == project_id)
        .order_by(PullRequest.pr_number.desc())
    )
    prs = result.scalars().all()
    return {
        "pull_requests": [
            {
                "id": str(pr.id),
                "number": pr.pr_number,
                "title": pr.title,
                "state": pr.state,
                "author": pr.author,
                "branch": pr.branch,
                "base_branch": pr.base_branch,
                "body": pr.body,
                "created_at": pr.pr_created_at,
                "updated_at": pr.pr_updated_at,
                "merged_at": pr.merged_at,
                "url": pr.url,
                "diff_url": pr.diff_url,
            }
            for pr in prs
        ],
        "total": len(prs),
    }


@app.get("/projects/{project_id}/files/{file_id}/content")
async def get_file_content(project_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    f = await db.get(File, file_id)
    if not f or str(f.project_id) != project_id:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content = git_service.get_file_content(project_id, f.path)
        return {"content": content, "encoding": "utf-8"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File content not found on disk")


# ── Review endpoints ──────────────────────────────────────────────────────────

@app.post("/review", response_model=ReviewResponseV2)
async def review_code(request: ReviewRequestV2, db: AsyncSession = Depends(get_db)):
    start = time.time()
    response = await run_review(request, force_memory_mode=request.force_memory_mode)
    elapsed_ms = int((time.time() - start) * 1000)
    review_id = str(uuid.uuid4())

    # Persist review
    if request.project_id:
        review = Review(
            id=review_id,
            project_id=request.project_id,
            file_id=request.file_id,
            code_snapshot=request.code[:5000],
            contributor=request.contributor,
            file_path=request.file_path,
            memory_mode=response.memory_mode,
            critical_issues=json.dumps(response.review.critical_issues),
            convention_violations=json.dumps(response.review.convention_violations),
            contributor_patterns=json.dumps(response.review.contributor_patterns),
            positive_signals=json.dumps(response.review.positive_signals),
            summary=response.review.summary,
            recalled_entries=json.dumps([e.model_dump() for e in response.recalled_entries]),
            groq_model=os.environ.get("GROQ_MODEL"),
            processing_time_ms=elapsed_ms,
        )
        db.add(review)
        # Increment review count
        p = await db.get(Project, request.project_id)
        if p:
            p.review_count = (p.review_count or 0) + 1
        await db.commit()

    return ReviewResponseV2(
        review=response.review,
        memory_mode=response.memory_mode,
        recalled_entries=response.recalled_entries,
        review_id=review_id,
        processing_time_ms=elapsed_ms,
    )


@app.get("/projects/{project_id}/reviews")
async def list_reviews(
    project_id: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Review)
        .where(Review.project_id == project_id)
        .order_by(Review.created_at.desc())
        .limit(limit).offset(offset)
    )
    reviews = result.scalars().all()
    return {
        "reviews": [
            {
                "id": str(r.id),
                "file_path": r.file_path,
                "contributor": r.contributor,
                "memory_mode": r.memory_mode,
                "summary": r.summary,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in reviews
        ]
    }


@app.get("/reviews/{review_id}")
async def get_review(review_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.get(Review, review_id)
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    return {
        "id": str(r.id),
        "code_snapshot": r.code_snapshot,
        "memory_mode": r.memory_mode,
        "contributor": r.contributor,
        "file_path": r.file_path,
        "review": {
            "critical_issues": json.loads(r.critical_issues or "[]"),
            "convention_violations": json.loads(r.convention_violations or "[]"),
            "contributor_patterns": json.loads(r.contributor_patterns or "[]"),
            "positive_signals": json.loads(r.positive_signals or "[]"),
            "summary": r.summary or "",
        },
        "recalled_entries": json.loads(r.recalled_entries or "[]"),
        "processing_time_ms": r.processing_time_ms,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


# ── Memory endpoints ──────────────────────────────────────────────────────────

@app.get("/memory")
async def get_memory():
    """Fetch all memories currently stored in the Hindsight bank."""
    entries = await hindsight.list_memories()
    return {"entries": [e.model_dump() for e in entries], "total": len(entries)}


@app.post("/inject-memory", response_model=InjectResponse)
async def inject_memory(request: InjectRequest):
    written = failed = 0
    errors: list[str] = []
    for entry in request.entries:
        if await hindsight.write_memory(entry):
            written += 1
        else:
            failed += 1
            errors.append(f"Failed: {entry.description[:60]}")
            break
    return InjectResponse(written=written, failed=failed, errors=errors)


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/projects/{project_id}/analytics")
async def get_analytics(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).where(Review.project_id == project_id))
    reviews = result.scalars().all()
    total = len(reviews)
    with_mem = sum(1 for r in reviews if r.memory_mode == "with")
    return {
        "total_reviews": total,
        "reviews_with_memory": with_mem,
        "reviews_without_memory": total - with_mem,
        "recent_reviews": [
            {"id": str(r.id), "file_path": r.file_path,
             "memory_mode": r.memory_mode,
             "created_at": r.created_at.isoformat() if r.created_at else ""}
            for r in sorted(reviews, key=lambda x: x.created_at or "", reverse=True)[:5]
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
