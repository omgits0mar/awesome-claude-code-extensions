#!/usr/bin/env python3
"""Shared catalog parsing and normalization helpers."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.parse
from collections.abc import Iterable
from pathlib import Path
from typing import Any


SNAPSHOT_MANIFEST = (
    Path(__file__).resolve().parents[1] / "research" / "snapshots" / "manifest.json"
)


def snapshot_checked_date() -> str:
    """Read the research date from the committed source manifest."""
    try:
        payload = json.loads(SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))
        value = str(payload["checked_at"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Cannot read a valid checked_at date from {SNAPSHOT_MANIFEST}"
        ) from exc
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise RuntimeError(f"Invalid snapshot checked_at date: {value!r}")
    return value


CHECKED_DATE = snapshot_checked_date()

SOURCE_DEFINITIONS: dict[str, dict[str, str]] = {
    "anthropic-marketplace": {
        "name": "Anthropic Claude Code Plugins Directory",
        "url": "https://github.com/anthropics/claude-plugins-official",
        "license": "Apache-2.0 (directory metadata; individual plugins vary)",
        "tier": "official",
    },
    "subinium-awesome": {
        "name": "subinium/awesome-claude-code",
        "url": "https://github.com/subinium/awesome-claude-code",
        "license": "CC0-1.0",
        "tier": "popular",
    },
    "manual-research": {
        "name": "Parallel web and GitHub research",
        "url": "https://github.com/topics/claude-code",
        "license": "Original catalog annotations; linked projects vary",
        "tier": "curated",
    },
    "punkpeye-mcp": {
        "name": "punkpeye/awesome-mcp-servers",
        "url": "https://github.com/punkpeye/awesome-mcp-servers",
        "license": "MIT (individual servers may vary)",
        "tier": "community",
    },
    "appcypher-mcp": {
        "name": "appcypher/awesome-mcp-servers",
        "url": "https://github.com/appcypher/awesome-mcp-servers",
        "license": "CC0-1.0",
        "tier": "curated",
    },
}

TIER_ORDER = {
    "official": 0,
    "popular": 1,
    "curated": 2,
    "community": 3,
}

KIND_ORDER = {
    "plugin": 0,
    "skill": 1,
    "command": 2,
    "hook": 3,
    "agent": 4,
    "workflow": 5,
    "mcp-server": 6,
    "mcp-tooling": 7,
    "interface": 8,
    "monitoring": 9,
    "learning": 10,
    "tool": 11,
    "collection": 12,
}

KIND_PAGE = {
    "plugin": "plugins",
    "skill": "skills-commands-hooks",
    "command": "skills-commands-hooks",
    "hook": "skills-commands-hooks",
    "agent": "agents-workflows",
    "workflow": "agents-workflows",
    "mcp-server": "mcp-servers",
    "mcp-tooling": "mcp-tooling",
    "interface": "tools-interfaces",
    "monitoring": "tools-interfaces",
    "tool": "tools-interfaces",
    "learning": "learning",
    "collection": "collections",
}

SOURCE_KIND_MAP = {
    "Official": "tool",
    "Configuration & Rules": "workflow",
    "Skills & Plugins": "skill",
    "Agent Orchestration": "agent",
    "GUI & IDE": "interface",
    "Monitoring & Analytics": "monitoring",
    "Learning & Reference": "learning",
    "Proxy & Customization": "tool",
    "Core & Frameworks": "mcp-tooling",
    "Servers": "mcp-server",
}

EMOJI_TAGS = {
    "🎖️": "official",
    "🐍": "python",
    "📇": "typescript-javascript",
    "🏎️": "go",
    "🦀": "rust",
    "#️⃣": "csharp",
    "☕": "java",
    "🌊": "cpp",
    "💎": "ruby",
    "☁️": "cloud",
    "🏠": "local",
    "📟": "embedded",
    "🍎": "macos",
    "🪟": "windows",
    "🐧": "linux",
}


def strip_markdown(value: str) -> str:
    """Turn a short Markdown description into readable plain text."""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"!\[[^\]]*]\([^)]*\)", " ", value)
    value = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = value.replace("**", "").replace("__", "").replace("*", "")
    value = re.sub(r"<https?://[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" -—\t")
    return value


def concise_description(value: str, max_length: int = 320) -> str:
    """Return one compact, factual sentence without cutting words."""
    value = strip_markdown(value)
    value = re.sub(r"\s*\(\s*Website\s*:[^)]+\)", "", value, flags=re.I)
    if not value:
        return "Public-source project for extending Claude Code or an MCP-compatible client."

    # Prefer the first complete sentence when the upstream prose is long.
    sentence_match = re.search(r"(?<=[A-Za-z0-9)\]])[.!?](?=\s|$)", value)
    # Ignore very early punctuation, which is more likely to be an
    # abbreviation such as "U.S." or "e.g." than a useful sentence.
    if sentence_match and sentence_match.end() >= 20:
        first = value[: sentence_match.end()].strip()
        if len(first) <= max_length:
            value = first

    if len(value) > max_length:
        clipped = value[: max_length - 1]
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:-")
        value = clipped + "…"
    elif value[-1] not in ".!?…":
        value += "."
    return value


def normalize_github_url(value: str) -> str | None:
    """Normalize a public GitHub URL while preserving meaningful subpaths."""
    if not value:
        return None
    value = html.unescape(value.strip()).strip("<>")
    value = value.replace("http://github.com/", "https://github.com/")
    parsed = urllib.parse.urlsplit(value)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return None
    path = re.sub(r"/+", "/", parsed.path).rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return None
    if (
        len(parts) == 4
        and parts[2] == "tree"
        and parts[3].lower() in {"main", "master"}
    ):
        parts = parts[:2]
    return "https://github.com/" + "/".join(parts)


def canonical_url(value: str) -> str:
    value = normalize_github_url(value) or value.strip().rstrip("/")
    return value.lower()


def github_repo_url(value: str) -> str | None:
    normalized = normalize_github_url(value)
    if not normalized:
        return None
    parts = urllib.parse.urlsplit(normalized).path.strip("/").split("/")
    return "https://github.com/" + "/".join(parts[:2])


def direct_tree_url(repo_url: str, ref: str, path: str) -> str | None:
    normalized = normalize_github_url(repo_url)
    if not normalized:
        return None
    ref = urllib.parse.quote(ref or "main", safe="-._~")
    # Remove a relative-path prefix without stripping meaningful dot-directories
    # such as `.github` or `.claude-plugin`.
    clean_path_value = path.strip()
    if clean_path_value.startswith("./"):
        clean_path_value = clean_path_value[2:]
    clean_path = "/".join(
        part for part in clean_path_value.strip("/").split("/") if part
    )
    if not clean_path:
        return normalized
    return f"{normalized}/tree/{ref}/{clean_path}"


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "entry"


def stable_id(name: str, url: str) -> str:
    path = urllib.parse.urlsplit(url).path.strip("/")
    base = slugify(path or name)
    if len(base) > 90:
        base = base[:80].rstrip("-")
    digest = hashlib.sha1(canonical_url(url).encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}"


def infer_tags(name: str, description: str, category: str) -> list[str]:
    haystack = f"{name} {description} {category}".lower()
    mapping = {
        "security": ("security", "vulnerability", "sast", "audit", "owasp"),
        "testing": ("test", "tdd", "playwright", "quality"),
        "database": ("database", "postgres", "mysql", "sqlite", "sql", "redis"),
        "browser": ("browser", "chrome", "playwright", "puppeteer", "web automation"),
        "documentation": ("documentation", "docs", "readme", "knowledge"),
        "git": ("git", "github", "pull request", "commit"),
        "devops": ("devops", "deployment", "kubernetes", "docker", "terraform", "cloud"),
        "design": ("design", "figma", "frontend", "ui", "ux"),
        "memory": ("memory", "context", "knowledge graph"),
        "observability": ("monitoring", "observability", "telemetry", "statusline"),
        "productivity": ("productivity", "workflow", "automation"),
        "data": ("analytics", "data", "spreadsheet", "research"),
        "communication": ("slack", "email", "gmail", "teams", "discord", "message"),
        "local-first": ("local-first", "fully local", "no cloud"),
    }
    result = [tag for tag, needles in mapping.items() if any(n in haystack for n in needles)]
    return sorted(set(result))


def source_record(source_id: str) -> dict[str, str]:
    source = SOURCE_DEFINITIONS[source_id]
    return {
        "name": source["name"],
        "url": source["url"],
    }


def new_entry(
    *,
    name: str,
    url: str,
    description: str,
    kind: str,
    category: str,
    source_id: str,
    tags: Iterable[str] = (),
    compatibility: Iterable[str] = ("claude-code",),
    official: bool = False,
    install: str | None = None,
    author: str | None = None,
    verification: str = "source-listed",
    license_name: str = "See upstream repository",
    notes: str | None = None,
    checked_at: str | None = None,
) -> dict[str, Any] | None:
    normalized = normalize_github_url(url)
    if not normalized:
        return None
    source = SOURCE_DEFINITIONS[source_id]
    cleaned_name = strip_markdown(name).strip() or normalized.rsplit("/", 1)[-1]
    cleaned_description = concise_description(description)
    compatibility_values = set(compatibility)
    all_tags = set(tags)
    all_tags.update(infer_tags(cleaned_name, cleaned_description, category))
    if kind == "mcp-server":
        all_tags.add("mcp")
    if "claude-code" in compatibility_values:
        all_tags.add("claude-code")
    if "codex" in compatibility_values:
        all_tags.add("codex")

    entry: dict[str, Any] = {
        "id": stable_id(cleaned_name, normalized),
        "name": cleaned_name,
        "aliases": [],
        "url": normalized,
        "repository_url": github_repo_url(normalized),
        "description": cleaned_description,
        "kind": kind if kind in KIND_ORDER else "tool",
        "category": strip_markdown(category) or "Other",
        "tags": sorted(tag for tag in all_tags if tag),
        "compatibility": sorted(compatibility_values),
        "source_tier": source["tier"],
        "official": bool(official),
        "install": install,
        "install_commands": [install] if install else [],
        "author": author,
        "license": license_name,
        "license_verified": False,
        "license_checked_at": None,
        "verification": verification,
        "last_checked": checked_at or CHECKED_DATE,
        "sources": [source_record(source_id)],
    }
    if notes:
        entry["notes"] = concise_description(notes)
    return entry


def merge_entries(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge exact URLs while retaining provenance from every source."""
    merged: dict[str, dict[str, Any]] = {}
    for entry in entries:
        key = canonical_url(entry["url"])
        existing = merged.get(key)
        if not existing:
            merged[key] = entry
            continue

        existing_rank = TIER_ORDER.get(existing["source_tier"], 99)
        candidate_rank = TIER_ORDER.get(entry["source_tier"], 99)
        preferred, secondary = (
            (entry, existing) if candidate_rank < existing_rank else (existing, entry)
        )
        preferred["tags"] = sorted(set(preferred["tags"]) | set(secondary["tags"]))
        preferred["compatibility"] = sorted(
            set(preferred["compatibility"]) | set(secondary["compatibility"])
        )
        preferred["official"] = preferred["official"] or secondary["official"]
        preferred["aliases"] = sorted(
            (
                set(preferred.get("aliases", []))
                | set(secondary.get("aliases", []))
                | (
                    {secondary["name"]}
                    if secondary["name"].lower() != preferred["name"].lower()
                    else set()
                )
            ),
            key=str.lower,
        )
        if secondary.get("license_verified") and not preferred.get("license_verified"):
            preferred["license"] = secondary["license"]
            preferred["license_verified"] = True
            preferred["license_checked_at"] = secondary.get("license_checked_at")
        if not preferred.get("install") and secondary.get("install"):
            preferred["install"] = secondary["install"]
        preferred["install_commands"] = sorted(
            set(preferred.get("install_commands", []))
            | set(secondary.get("install_commands", []))
        )
        if not preferred.get("author") and secondary.get("author"):
            preferred["author"] = secondary["author"]
        seen_sources = {canonical_url(item["url"]) for item in preferred["sources"]}
        for item in secondary["sources"]:
            if canonical_url(item["url"]) not in seen_sources:
                preferred["sources"].append(item)
                seen_sources.add(canonical_url(item["url"]))
        preferred["sources"].sort(key=lambda item: item["name"].lower())
        merged[key] = preferred

    result = list(merged.values())
    result.sort(
        key=lambda item: (
            TIER_ORDER.get(item["source_tier"], 99),
            KIND_ORDER.get(item["kind"], 99),
            item["category"].lower(),
            item["name"].lower(),
            item["url"].lower(),
        )
    )
    return result


def markdown_anchor(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[\s_-]+", "-", value).strip("-")
