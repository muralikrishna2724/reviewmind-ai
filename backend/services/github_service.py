"""GitHub API client for fetching pull requests."""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any


def _parse_github_url(url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL. Returns None if not a GitHub URL."""
    match = re.search(r"github\.com[/:]([^/]+)/([^/\\.]+)", url)
    if not match:
        return None
    return match.group(1), match.group(2).rstrip(".git")


def _api_request(path: str) -> Any:
    """Make an authenticated GitHub API request. Returns parsed JSON."""
    token = os.environ.get("GITHUB_TOKEN", "")
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def fetch_pull_requests(repo_url: str, state: str = "all", per_page: int = 30) -> list[dict[str, Any]]:
    """Fetch pull requests for a GitHub repository.

    Args:
        repo_url: Full GitHub repository URL.
        state: 'open', 'closed', or 'all'.
        per_page: Max PRs to fetch (max 100).

    Returns:
        List of PR dicts with keys: number, title, state, author, branch,
        base_branch, body, created_at, updated_at, merged_at, url, diff_url.
    """
    parsed = _parse_github_url(repo_url)
    if not parsed:
        raise ValueError(f"Not a valid GitHub URL: {repo_url}")

    owner, repo = parsed
    data = _api_request(f"/repos/{owner}/{repo}/pulls?state={state}&per_page={per_page}&sort=updated&direction=desc")

    prs = []
    for pr in data:
        prs.append({
            "number": pr["number"],
            "title": pr["title"],
            "state": pr["state"],
            "author": pr.get("user", {}).get("login", ""),
            "branch": pr.get("head", {}).get("ref", ""),
            "base_branch": pr.get("base", {}).get("ref", ""),
            "body": pr.get("body") or "",
            "created_at": pr.get("created_at", ""),
            "updated_at": pr.get("updated_at", ""),
            "merged_at": pr.get("merged_at"),
            "url": pr.get("html_url", ""),
            "diff_url": pr.get("diff_url", ""),
        })
    return prs
