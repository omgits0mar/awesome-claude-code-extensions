#!/usr/bin/env python3
"""Validate catalog integrity without third-party dependencies."""

from __future__ import annotations

import csv
import json
import re
import sys
import urllib.parse
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "catalog.json"
LINK_OVERRIDES_PATH = ROOT / "catalog" / "link-overrides.json"
EXCLUSIONS_PATH = ROOT / "catalog" / "exclusions.json"
ALLOWED_TIERS = {"official", "popular", "curated", "community"}
ALLOWED_KINDS = {
    "plugin",
    "skill",
    "command",
    "hook",
    "agent",
    "workflow",
    "mcp-server",
    "mcp-tooling",
    "interface",
    "monitoring",
    "learning",
    "tool",
    "collection",
}
REQUIRED_FIELDS = {
    "id",
    "name",
    "aliases",
    "url",
    "repository_url",
    "description",
    "kind",
    "category",
    "tags",
    "compatibility",
    "source_tier",
    "official",
    "install",
    "install_commands",
    "author",
    "license",
    "license_verified",
    "license_checked_at",
    "verification",
    "last_checked",
    "sources",
}
ALLOWED_FIELDS = REQUIRED_FIELDS | {"notes"}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    if not CATALOG_PATH.exists():
        print(f"Missing {CATALOG_PATH}", file=sys.stderr)
        return 1
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if not isinstance(entries, list):
        print("catalog.entries must be an array", file=sys.stderr)
        return 1
    if payload.get("schema_version") != "1.0.0":
        fail(errors, "schema_version must be 1.0.0")
    if len(entries) < 500:
        fail(errors, f"catalog quality floor is 500 entries; found {len(entries)}")

    ids: set[str] = set()
    urls: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"entry[{index}]"
        missing = REQUIRED_FIELDS - set(entry)
        if missing:
            fail(errors, f"{label} missing fields: {sorted(missing)}")
            continue
        unexpected = set(entry) - ALLOWED_FIELDS
        if unexpected:
            fail(errors, f"{label} has unsupported fields: {sorted(unexpected)}")
        entry_id = entry["id"]
        if not isinstance(entry_id, str) or not re.fullmatch(r"[a-z0-9-]+", entry_id):
            fail(errors, f"{label} has invalid id: {entry_id!r}")
        elif entry_id in ids:
            fail(errors, f"duplicate id: {entry_id}")
        ids.add(entry_id)

        url = entry["url"]
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
            fail(errors, f"{label} is not a canonical HTTPS GitHub URL: {url}")
        canonical = url.lower().rstrip("/")
        if canonical in urls:
            fail(errors, f"duplicate URL: {url}")
        urls.add(canonical)

        repo_url = entry["repository_url"]
        repo_parts = urllib.parse.urlsplit(repo_url).path.strip("/").split("/")
        if len(repo_parts) != 2:
            fail(errors, f"{label} has invalid repository_url: {repo_url}")
        url_parts = parsed.path.strip("/").split("/")
        expected_repo_url = (
            f"https://github.com/{url_parts[0]}/{url_parts[1]}"
            if len(url_parts) >= 2
            else ""
        )
        if expected_repo_url.lower() != repo_url.lower():
            fail(errors, f"{label} repository_url is not canonical")

        description = entry["description"]
        if not isinstance(description, str) or len(description) < 15:
            fail(errors, f"{label} has a missing/short description")
        if len(description) > 320:
            fail(errors, f"{label} description exceeds 320 characters")
        if entry["kind"] not in ALLOWED_KINDS:
            fail(errors, f"{label} has unsupported kind: {entry['kind']}")
        if entry["source_tier"] not in ALLOWED_TIERS:
            fail(errors, f"{label} has unsupported source tier: {entry['source_tier']}")
        if not isinstance(entry["official"], bool):
            fail(errors, f"{label} official must be boolean")
        if not isinstance(entry["license_verified"], bool):
            fail(errors, f"{label} license_verified must be boolean")
        for nullable in ("install", "author"):
            if entry[nullable] is not None and not isinstance(entry[nullable], str):
                fail(errors, f"{label} {nullable} must be a string or null")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["last_checked"]):
            fail(errors, f"{label} has invalid last_checked date")
        license_checked_at = entry["license_checked_at"]
        if entry["license_verified"] and not (
            isinstance(license_checked_at, str)
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", license_checked_at)
        ):
            fail(errors, f"{label} has verified license without a check date")
        if not entry["license_verified"] and license_checked_at is not None:
            fail(errors, f"{label} has a license check date but is not verified")
        if not isinstance(entry["tags"], list) or entry["tags"] != sorted(set(entry["tags"])):
            fail(errors, f"{label} tags must be a sorted unique array")
        if (
            not isinstance(entry["aliases"], list)
            or entry["aliases"] != sorted(set(entry["aliases"]), key=str.lower)
        ):
            fail(errors, f"{label} aliases must be a sorted unique array")
        if (
            not isinstance(entry["compatibility"], list)
            or entry["compatibility"] != sorted(set(entry["compatibility"]))
        ):
            fail(errors, f"{label} compatibility must be a sorted unique array")
        if (
            not isinstance(entry["install_commands"], list)
            or entry["install_commands"] != sorted(set(entry["install_commands"]))
        ):
            fail(errors, f"{label} install_commands must be a sorted unique array")
        if entry["install"] and entry["install"] not in entry["install_commands"]:
            fail(errors, f"{label} primary install is missing from install_commands")
        if not isinstance(entry["sources"], list) or not entry["sources"]:
            fail(errors, f"{label} must include provenance")
        for source in entry["sources"]:
            if set(source) != {"name", "url"}:
                fail(errors, f"{label} source provenance has unsupported fields")
            if not source.get("name") or not source.get("url"):
                fail(errors, f"{label} has malformed source provenance")

    counts = payload.get("counts", {})
    if counts.get("total") != len(entries):
        fail(errors, "counts.total does not match entry count")
    repo_count = len({entry["repository_url"].lower() for entry in entries})
    if counts.get("github_repositories") != repo_count:
        fail(errors, "counts.github_repositories does not match data")
    verified_license_count = sum(entry["license_verified"] for entry in entries)
    if counts.get("license_verified") != verified_license_count:
        fail(errors, "counts.license_verified does not match data")
    official_provider_count = sum(entry["official"] for entry in entries)
    if counts.get("official_provider") != official_provider_count:
        fail(errors, "counts.official_provider does not match data")
    actual_by_kind = dict(sorted(Counter(entry["kind"] for entry in entries).items()))
    if counts.get("by_kind") != actual_by_kind:
        fail(errors, "counts.by_kind does not match data")
    actual_by_tier = Counter(entry["source_tier"] for entry in entries)
    if dict(actual_by_tier) != counts.get("by_tier"):
        # Ordering is irrelevant after JSON decoding, values are not.
        if actual_by_tier != Counter(counts.get("by_tier", {})):
            fail(errors, "counts.by_tier does not match data")
    if actual_by_tier.get("official", 0) < 200:
        fail(errors, "expected at least 200 official-tier plugin entries")
    if counts.get("official_directory") != actual_by_tier.get("official", 0):
        fail(errors, "counts.official_directory does not match data")
    if actual_by_kind.get("mcp-server", 0) < 800:
        fail(errors, "expected at least 800 MCP server entries")

    stats_path = ROOT / "catalog" / "stats.json"
    if stats_path.exists():
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        if stats != counts:
            fail(errors, "catalog/stats.json does not match catalog counts")

    csv_path = ROOT / "catalog" / "catalog.csv"
    if csv_path.exists():
        with csv_path.open(encoding="utf-8", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        if len(csv_rows) != len(entries):
            fail(errors, "catalog/catalog.csv row count does not match entries")
        csv_urls = {
            row.get("url", "").removeprefix("'").lower().rstrip("/")
            for row in csv_rows
        }
        if csv_urls != urls:
            fail(errors, "catalog/catalog.csv URLs do not match catalog entries")

    if not LINK_OVERRIDES_PATH.exists():
        fail(errors, "missing catalog/link-overrides.json")
    else:
        overrides = json.loads(LINK_OVERRIDES_PATH.read_text(encoding="utf-8"))
        override_urls: set[str] = set()
        catalog_urls = {entry["url"].lower().rstrip("/") for entry in entries}
        expected_exclusions: set[str] = set()
        for index, override in enumerate(overrides):
            label = f"link override[{index}]"
            url = str(override.get("url") or "").lower().rstrip("/")
            action = override.get("action")
            if not url.startswith("https://github.com/"):
                fail(errors, f"{label} has an invalid source URL")
            if url in override_urls:
                fail(errors, f"duplicate link override: {override.get('url')}")
            override_urls.add(url)
            if action == "exclude":
                expected_exclusions.add(url)
                if url in catalog_urls:
                    fail(errors, f"excluded URL remains in catalog: {override.get('url')}")
            elif action == "replace":
                replacement = str(
                    override.get("replacement_url") or ""
                ).lower().rstrip("/")
                if replacement not in catalog_urls:
                    fail(
                        errors,
                        f"replacement URL is missing from catalog: "
                        f"{override.get('replacement_url')}",
                    )
            else:
                fail(errors, f"{label} has unsupported action: {action!r}")

        if not EXCLUSIONS_PATH.exists():
            fail(errors, "missing generated catalog/exclusions.json")
        else:
            exclusions = json.loads(EXCLUSIONS_PATH.read_text(encoding="utf-8"))
            rendered_exclusions = {
                str(item.get("url") or "").lower().rstrip("/")
                for item in exclusions
            }
            if rendered_exclusions != expected_exclusions:
                fail(errors, "catalog/exclusions.json does not match link overrides")

    generated_files = [
        ROOT / "CATALOG.md",
        ROOT / "catalog" / "catalog.csv",
        ROOT / "catalog" / "stats.json",
        ROOT / "catalog" / "schema.json",
        ROOT / "catalog" / "verified-open-source.md",
        ROOT / "catalog" / "by-kind" / "plugins.md",
        ROOT / "catalog" / "by-kind" / "mcp-servers.md",
    ]
    for path in generated_files:
        if not path.exists() or path.stat().st_size == 0:
            fail(errors, f"missing generated artifact: {path.relative_to(ROOT)}")

    if errors:
        print(f"Validation failed with {len(errors)} error(s):", file=sys.stderr)
        for message in errors[:100]:
            print(f"- {message}", file=sys.stderr)
        if len(errors) > 100:
            print(f"- …and {len(errors) - 100} more", file=sys.stderr)
        return 1

    print(
        f"Validated {len(entries):,} entries across {repo_count:,} GitHub repositories; "
        f"{actual_by_kind.get('mcp-server', 0):,} MCP servers and "
        f"{actual_by_tier.get('official', 0):,} official-tier entries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
