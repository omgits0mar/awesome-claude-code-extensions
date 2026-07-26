#!/usr/bin/env python3
"""Discover candidate Claude Code extension repositories with GitHub Code Search.

This intentionally writes to a review queue. Search hits are never auto-published
into the curated catalog.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUERIES = [
    'path:.claude-plugin filename:plugin.json "claude"',
    'path:.claude-plugin filename:marketplace.json "plugins"',
    'filename:SKILL.md "Claude Code"',
    'path:.claude/commands extension:md "description"',
    'path:.claude/agents extension:md "tools"',
    'path:.claude/hooks extension:json',
]


def search(query: str, token: str, pages: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        params = urllib.parse.urlencode(
            {"q": query, "per_page": 100, "page": page}
        )
        request = urllib.request.Request(
            f"https://api.github.com/search/code?{params}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "awesome-claude-code-catalog-discovery/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
        results.extend(payload.get("items", []))
        if len(payload.get("items", [])) < 100:
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=2, help="Pages per search query.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research" / "github-discovery-candidates.json",
    )
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN")
    if not token:
        parser.error("GH_TOKEN is required for GitHub Code Search.")

    repos: dict[str, dict[str, Any]] = {}
    for query in QUERIES:
        for item in search(query, token, args.pages):
            repo = item.get("repository") or {}
            full_name = repo.get("full_name")
            if not full_name:
                continue
            record = repos.setdefault(
                full_name.lower(),
                {
                    "name": full_name,
                    "url": repo.get("html_url"),
                    "description": repo.get("description") or "",
                    "matched_queries": [],
                    "matched_files": [],
                    "review_status": "pending",
                },
            )
            record["matched_queries"].append(query)
            record["matched_files"].append(item.get("html_url"))

    candidates = sorted(repos.values(), key=lambda item: item["name"].lower())
    for candidate in candidates:
        candidate["matched_queries"] = sorted(set(candidate["matched_queries"]))
        candidate["matched_files"] = sorted(set(candidate["matched_files"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(candidates):,} candidates to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
