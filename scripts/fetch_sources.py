#!/usr/bin/env python3
"""Fetch public upstream catalog snapshots used by the reproducible build."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "anthropic-marketplace.json": (
        "https://api.github.com/repos/anthropics/claude-plugins-official/"
        "contents/.claude-plugin/marketplace.json"
    ),
    "subinium-awesome.md.txt": (
        "https://api.github.com/repos/subinium/awesome-claude-code/readme"
    ),
    "punkpeye-mcp.md.txt": (
        "https://api.github.com/repos/punkpeye/awesome-mcp-servers/readme"
    ),
    "appcypher-mcp.md.txt": (
        "https://api.github.com/repos/appcypher/awesome-mcp-servers/readme"
    ),
}


def fetch(url: str, token: str | None = None) -> bytes:
    headers = {
        "Accept": "application/vnd.github.raw+json",
        "User-Agent": "awesome-claude-code-catalog/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research" / "snapshots",
        help="Committed snapshot destination.",
    )
    parser.add_argument(
        "--github-token",
        default=None,
        help="Optional GitHub token. Prefer the GH_TOKEN environment variable in automation.",
    )
    args = parser.parse_args()

    import os

    token = args.github_token or os.environ.get("GH_TOKEN")
    failures = 0
    manifest_sources: dict[str, dict[str, str]] = {}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".catalog-snapshots-", dir=args.output.parent
    ) as temporary:
        staging = Path(temporary)
        for filename, url in SOURCES.items():
            try:
                data = fetch(url, token=token)
                if filename.endswith(".json"):
                    json.loads(data.decode("utf-8"))
                (staging / filename).write_bytes(data)
                manifest_sources[filename] = {
                    "url": url,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                print(f"Fetched {filename}: {len(data):,} bytes")
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                failures += 1
                print(f"ERROR {filename}: {exc}")
        if failures:
            print("Snapshot refresh aborted; committed inputs were left unchanged.")
            return 1

        manifest = {
            "schema_version": "1.0.0",
            "checked_at": datetime.now(timezone.utc).date().isoformat(),
            "description": (
                "Committed upstream snapshots used for deterministic catalog builds."
            ),
            "sources": dict(sorted(manifest_sources.items())),
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        args.output.mkdir(parents=True, exist_ok=True)
        for filename in SOURCES:
            shutil.copyfile(staging / filename, args.output / filename)
        shutil.copyfile(staging / "manifest.json", args.output / "manifest.json")
        print(
            f"Refreshed {len(manifest_sources):,} committed snapshots and manifest"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
