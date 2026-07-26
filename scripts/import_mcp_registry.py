#!/usr/bin/env python3
"""Create a review queue from the official MCP Registry.

The official registry is intentionally unopinionated and may include closed-source
or deleted packages. This importer keeps active records with public GitHub
repository metadata, but it does not merge them into the curated catalog.
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"
META_KEY = "io.modelcontextprotocol.registry/official"


def fetch_page(cursor: str | None) -> dict[str, Any]:
    params = {"limit": 100, "version": "latest"}
    if cursor:
        params["cursor"] = cursor
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "awesome-claude-code-catalog-registry-importer/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def github_repository(record: dict[str, Any]) -> str | None:
    registry_meta = (record.get("_meta") or {}).get(META_KEY) or {}
    repository = registry_meta.get("repository") or record.get("repository") or {}
    url = repository.get("url") if isinstance(repository, dict) else None
    if not isinstance(url, str):
        return None
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc.lower() != "github.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    return f"https://github.com/{parts[0]}/{parts[1].removesuffix('.git')}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages", type=int, default=0, help="0 imports all pages.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research" / "official-mcp-registry-candidates.json",
    )
    args = parser.parse_args()
    cursor: str | None = None
    candidates: dict[str, dict[str, Any]] = {}
    page = 0
    while True:
        page += 1
        payload = fetch_page(cursor)
        for wrapper in payload.get("servers", []):
            server = wrapper.get("server") or wrapper
            registry_meta = (wrapper.get("_meta") or {}).get(META_KEY) or {}
            status = registry_meta.get("status") or server.get("status") or "active"
            if status != "active":
                continue
            repo_url = github_repository(wrapper) or github_repository(server)
            if not repo_url:
                continue
            name = server.get("name") or repo_url.rsplit("/", 1)[-1]
            candidates[repo_url.lower()] = {
                "name": name,
                "url": repo_url,
                "description": server.get("description") or "",
                "registry_name": server.get("name"),
                "version": registry_meta.get("version") or server.get("version"),
                "source_list_url": BASE_URL,
                "review_status": "pending",
                "license_status": "unverified",
            }
        metadata = payload.get("metadata") or {}
        cursor = metadata.get("nextCursor") or metadata.get("next_cursor")
        print(f"page {page}: {len(candidates):,} GitHub candidates")
        if not cursor or (args.max_pages and page >= args.max_pages):
            break

    output = sorted(candidates.values(), key=lambda item: item["name"].lower())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(output):,} candidates to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
