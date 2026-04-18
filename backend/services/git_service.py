"""Git repository cloning and file tree parsing."""
from __future__ import annotations

import json
import os
import re
import shutil
import urllib.request
from pathlib import Path
from typing import Any

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
}

EXT_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "react", ".tsx": "react", ".java": "java",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".cs": "csharp",
    ".cpp": "cpp", ".c": "c", ".php": "php", ".swift": "swift",
    ".kt": "kotlin", ".md": "markdown", ".json": "json",
    ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
}

STORAGE_ROOT = Path(os.environ.get("STORAGE_PATH", "./storage/projects"))


def _file_type(filename: str) -> str:
    return EXT_MAP.get(Path(filename).suffix.lower(), "text")


def _inject_token(url: str) -> str:
    """Inject GITHUB_TOKEN into a GitHub HTTPS URL if available."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if token and "github.com" in url and url.startswith("https://"):
        return url.replace("https://", f"https://{token}@", 1)
    return url


def _github_default_branch(owner: str, repo: str) -> str | None:
    """Fetch the default branch from the GitHub API (works for public repos without a token)."""
    token = os.environ.get("GITHUB_TOKEN", "")
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    req = urllib.request.Request(api_url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("default_branch")
    except Exception:
        return None


async def clone_repository(url: str, project_id: str, branch: str = "main") -> dict[str, Any]:
    """Clone a git repository. Returns clone metadata.

    - Injects GITHUB_TOKEN for private repo access.
    - If the requested branch doesn't exist, auto-detects the real default
      branch via the GitHub API and retries automatically.
    """
    try:
        from git import Repo, GitCommandError
    except ImportError:
        raise RuntimeError("GitPython not installed. Run: pip install GitPython")

    clone_url = _inject_token(url)
    project_dir = STORAGE_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # Extract owner/repo slug for GitHub API fallback
    gh_match = re.search(r"github\.com[/:]([^/]+)/([^/\\.]+)", url)

    try:
        repo = Repo.clone_from(clone_url, str(project_dir), branch=branch, depth=1)
    except GitCommandError:
        # Branch not found — detect the real default branch via GitHub API
        actual_branch = None
        if gh_match:
            actual_branch = _github_default_branch(gh_match.group(1), gh_match.group(2).rstrip(".git"))

        # Build list of branches to try
        candidates = []
        if actual_branch and actual_branch != branch:
            candidates.append(actual_branch)
        for fallback in ("master", "main", "develop"):
            if fallback != branch and fallback not in candidates:
                candidates.append(fallback)

        repo = None
        used_branch = branch
        for candidate in candidates:
            shutil.rmtree(str(project_dir), ignore_errors=True)
            project_dir.mkdir(parents=True, exist_ok=True)
            try:
                repo = Repo.clone_from(clone_url, str(project_dir), branch=candidate, depth=1)
                used_branch = candidate
                break
            except GitCommandError:
                continue

        if repo is None:
            raise RuntimeError(
                f"Could not clone '{url}': branch '{branch}' not found. "
                f"Tried: {', '.join(candidates) or 'none'}. "
                "Check the repository URL and branch name."
            )
        branch = used_branch

    return {
        "path": str(project_dir),
        "branch": branch,
        "commit": repo.head.commit.hexsha[:8],
    }


def parse_file_tree(project_dir: Path) -> list[dict[str, Any]]:
    """Walk directory and return file metadata list."""
    tree: list[dict[str, Any]] = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        rel_root = Path(root).relative_to(project_dir)
        for fname in files:
            fpath = Path(root) / fname
            try:
                size = fpath.stat().st_size
            except OSError:
                size = 0
            tree.append({
                "path": str(rel_root / fname),
                "name": fname,
                "size": size,
                "type": _file_type(fname),
            })
    return tree


def get_file_content(project_id: str, file_path: str) -> str:
    """Read file content from cloned repo."""
    full_path = STORAGE_ROOT / project_id / file_path
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return full_path.read_text(encoding="utf-8", errors="replace")
