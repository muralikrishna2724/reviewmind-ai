"""Git repository cloning and file tree parsing."""
from __future__ import annotations

import os
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


async def clone_repository(url: str, project_id: str, branch: str = "main") -> dict[str, Any]:
    """Clone a git repository. Returns clone metadata.

    If GITHUB_TOKEN is set and the URL is a GitHub HTTPS URL, the token is
    injected so private repositories can be cloned without interactive auth.
    """
    try:
        from git import Repo
    except ImportError:
        raise RuntimeError("GitPython not installed. Run: pip install GitPython")

    # Inject GitHub token for private repo access
    clone_url = url
    token = os.environ.get("GITHUB_TOKEN", "")
    if token and "github.com" in url and url.startswith("https://"):
        # Transform https://github.com/... → https://<token>@github.com/...
        clone_url = url.replace("https://", f"https://{token}@", 1)

    project_dir = STORAGE_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    repo = Repo.clone_from(clone_url, str(project_dir), branch=branch, depth=1)
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
