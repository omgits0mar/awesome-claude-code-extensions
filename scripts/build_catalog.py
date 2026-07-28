#!/usr/bin/env python3
"""Build the human- and machine-readable Claude Code and Codex extension catalog."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from catalog_lib import (
    CHECKED_DATE,
    EMOJI_TAGS,
    KIND_ORDER,
    KIND_PAGE,
    SOURCE_DEFINITIONS,
    SOURCE_KIND_MAP,
    TIER_ORDER,
    canonical_url,
    concise_description,
    direct_tree_url,
    github_repo_url,
    merge_entries,
    new_entry,
    normalize_github_url,
    slugify,
    stable_id,
    strip_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "research" / "snapshots"
LINK_OVERRIDES_PATH = ROOT / "catalog" / "link-overrides.json"
RESEARCH_MANIFEST_PATH = ROOT / "research" / "manifest.json"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_source_manifest(source_dir: Path) -> None:
    """Refuse to build from unrecorded or modified upstream snapshots."""
    manifest_path = source_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing source manifest: {manifest_path}")
    manifest = load_json(manifest_path)
    if manifest.get("checked_at") != CHECKED_DATE:
        raise ValueError(
            "Snapshot manifest date differs from the catalog checked date"
        )
    sources = manifest.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Snapshot manifest must list source files")
    for filename, metadata in sources.items():
        path = source_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing committed snapshot: {path}")
        expected = str((metadata or {}).get("sha256") or "")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if not expected or actual != expected:
            raise ValueError(
                f"Snapshot checksum mismatch for {filename}: "
                f"expected {expected or '<missing>'}, got {actual}"
            )


def load_research_manifest() -> dict[str, dict[str, str]]:
    """Validate manually researched datasets and return their dated metadata."""
    manifest = load_json(RESEARCH_MANIFEST_PATH)
    datasets = manifest.get("datasets")
    if not isinstance(datasets, dict) or not datasets:
        raise ValueError("research/manifest.json must list datasets")
    for filename, metadata in datasets.items():
        path = ROOT / "research" / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing research dataset: {path}")
        expected = str((metadata or {}).get("sha256") or "")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        checked_at = str((metadata or {}).get("checked_at") or "")
        if expected != actual:
            raise ValueError(f"Research checksum mismatch for {filename}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked_at):
            raise ValueError(f"Invalid research checked_at date for {filename}")
    return datasets


def load_link_overrides() -> list[dict[str, Any]]:
    """Load reviewed replacements and exclusions for stale upstream links."""
    if not LINK_OVERRIDES_PATH.exists():
        return []
    payload = load_json(LINK_OVERRIDES_PATH)
    if not isinstance(payload, list):
        raise ValueError("catalog/link-overrides.json must contain an array")

    seen: set[str] = set()
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"link override {index} must be an object")
        url = normalize_github_url(str(item.get("url") or ""))
        action = item.get("action")
        if not url or action not in {"exclude", "replace"}:
            raise ValueError(f"link override {index} has an invalid URL or action")
        key = canonical_url(url)
        if key in seen:
            raise ValueError(f"duplicate link override for {url}")
        seen.add(key)
        if action == "replace" and not normalize_github_url(
            str(item.get("replacement_url") or "")
        ):
            raise ValueError(f"replacement override for {url} has no valid target")
    return payload


def apply_link_overrides(
    entries: list[dict[str, Any]], overrides: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply reviewed URL moves and remove unavailable canonical sources."""
    by_url = {
        canonical_url(str(item["url"])): item
        for item in overrides
    }
    output: list[dict[str, Any]] = []
    replacements = 0
    exclusions = 0
    for entry in entries:
        override = by_url.get(canonical_url(entry["url"]))
        if not override:
            output.append(entry)
            continue
        if override["action"] == "exclude":
            exclusions += 1
            continue

        replacement = normalize_github_url(str(override["replacement_url"]))
        assert replacement
        entry["url"] = replacement
        entry["repository_url"] = github_repo_url(replacement)
        entry["id"] = stable_id(entry["name"], replacement)
        note = str(override.get("reason") or "Canonical repository URL updated.")
        entry["notes"] = concise_description(note)
        replacements += 1
        output.append(entry)
    print(
        f"link overrides: {replacements:,} source record(s) replaced; "
        f"{exclusions:,} excluded"
    )
    return output


def write_exclusions(overrides: list[dict[str, Any]]) -> None:
    """Render the exclusion-only review queue from the override ledger."""
    exclusions = []
    for item in overrides:
        if item["action"] != "exclude":
            continue
        exclusions.append(
            {
                "url": item["url"],
                "reason": item["reason"],
                "evidence": item.get("evidence"),
                "checked_at": item.get("checked_at", CHECKED_DATE),
                "review_after": item.get("review_after", "2026-08-26"),
            }
        )
    exclusions.sort(key=lambda item: item["url"].lower())
    (ROOT / "catalog" / "exclusions.json").write_text(
        json.dumps(exclusions, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def parse_anthropic_marketplace(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    entries: list[dict[str, Any]] = []
    for plugin in payload.get("plugins", []):
        source = plugin.get("source")
        url: str | None = None
        if isinstance(source, str):
            url = direct_tree_url(
                "https://github.com/anthropics/claude-plugins-official",
                "main",
                source,
            )
        elif isinstance(source, dict):
            source_type = source.get("source")
            base: str | None = None
            if source_type == "github" and source.get("repo"):
                base = normalize_github_url(f"https://github.com/{source['repo']}")
            elif source.get("url"):
                base = normalize_github_url(str(source["url"]))
            if base and source.get("path"):
                url = direct_tree_url(
                    base,
                    str(source.get("sha") or source.get("ref") or "main"),
                    str(source["path"]),
                )
            else:
                url = base
        if not url:
            continue

        author = plugin.get("author")
        if isinstance(author, dict):
            author = author.get("name")
        elif not isinstance(author, str):
            author = None
        raw_tags = plugin.get("tags") or plugin.get("keywords") or []
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        name = plugin.get("displayName") or plugin.get("name") or "Unnamed plugin"
        category = str(plugin.get("category") or "other").replace("-", " ").title()
        entry = new_entry(
            name=name,
            url=url,
            description=str(plugin.get("description") or ""),
            kind="plugin",
            category=category,
            source_id="anthropic-marketplace",
            tags=[str(tag).lower().replace(" ", "-") for tag in raw_tags],
            compatibility=("claude-code",),
            official=True,
            install=f"/plugin install {plugin.get('name')}@claude-plugins-official",
            author=author,
            verification="official-marketplace",
            license_name="See the linked plugin repository",
            notes="Listed in Anthropic's official directory; inclusion is not a security audit.",
        )
        if entry:
            entries.append(entry)
    return entries


TABLE_ROW = re.compile(
    r"^\|\s*\[([^\]]+)]\((https?://github\.com/[^)\s]+)\)\s*\|.*?\|\s*(.*?)\s*\|\s*$"
)


def parse_subinium(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    section = "Other"
    subsection = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = strip_markdown(line[3:]).strip()
            subsection = ""
            continue
        if line.startswith("### "):
            subsection = strip_markdown(line[4:]).strip()
            continue
        match = TABLE_ROW.match(line)
        if not match:
            continue
        name, url, description = match.groups()
        kind_key = subsection or section
        kind = SOURCE_KIND_MAP.get(kind_key, SOURCE_KIND_MAP.get(section, "tool"))
        if kind_key == "Skills & Plugins" or section == "Skills & Plugins":
            haystack = f"{name} {description}".lower()
            if any(
                marker in haystack
                for marker in ("awesome-", "curated list", "skills list", "directory")
            ):
                kind = "collection"
            elif "plugin" in haystack:
                kind = "plugin"
            elif "statusline" in haystack or "status line" in haystack:
                kind = "monitoring"
            elif "skill" in haystack:
                kind = "skill"
        category = f"{section} / {subsection}" if subsection else section
        if kind == "skill":
            compatibility = ("agent-skills", "claude-code", "codex")
        elif kind == "mcp-server":
            compatibility = ("claude-code", "codex", "mcp")
        elif kind == "mcp-tooling":
            compatibility = ("claude-code", "mcp")
        else:
            compatibility = ("claude-code",)
        entry = new_entry(
            name=name,
            url=url,
            description=description,
            kind=kind,
            category=category,
            source_id="subinium-awesome",
            tags=("popular",),
            compatibility=compatibility,
            official=section == "Official",
            verification="popular-list",
            license_name="See upstream repository",
            notes="The source list required at least 1,000 GitHub stars at snapshot time.",
        )
        if entry:
            entries.append(entry)
    return entries


BULLET_GITHUB_LINK = re.compile(
    r"\[([^\]]+)]\((https?://github\.com/[^)\s]+)\)", re.I
)


def description_after_project(line: str, match: re.Match[str]) -> str:
    remainder = line[match.end() :]
    # Most source lists use a spaced dash after badges, author links, or icons.
    parts = re.split(r"\s+-\s+", remainder, maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    return remainder.strip(" -")


def parse_punkpeye(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    category = "Other"
    in_server_section = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            heading = strip_markdown(re.sub(r"<[^>]+>", "", line[3:])).strip()
            in_server_section = heading == "Server Implementations"
            continue
        if not in_server_section:
            continue
        if line.startswith("### "):
            heading = re.sub(r"<[^>]+>", "", line[4:])
            category = strip_markdown(heading).strip()
            continue
        if not line.startswith(("- ", "* ")):
            continue
        match = BULLET_GITHUB_LINK.search(line)
        if not match:
            continue
        name, url = match.groups()
        # Skip badge links accidentally selected as the first GitHub link.
        if "badge" in name.lower() or "/actions/" in url:
            continue
        description = description_after_project(line, match)
        # Some entries use a non-GitHub homepage first and put the canonical
        # GitHub repository in a trailing "(Source)" link.
        primary = re.match(r"^[-*]\s+\[([^\]]+)]\([^)]+\)", line)
        if primary and name.strip().lower() in {"source", "github", "repository", "repo"}:
            name = primary.group(1)
            description = re.split(r"\s+-\s+", line, maxsplit=1)[-1]
            description = re.sub(
                r"\s*\(\[(?:Source|GitHub|Repository|Repo)]\([^)]+\)\)\s*$",
                "",
                description,
                flags=re.I,
            )
        if not strip_markdown(description):
            description = f"{name} is a community-listed public-source MCP server."
        tags = [tag for emoji, tag in EMOJI_TAGS.items() if emoji in line]
        entry = new_entry(
            name=name,
            url=url,
            description=description,
            kind="mcp-server",
            category=category,
            source_id="punkpeye-mcp",
            tags=tags,
            compatibility=("claude-code", "codex", "mcp"),
            official="official" in tags,
            verification="community-awesome-list",
            license_name="See upstream repository",
            notes="Community-listed MCP server; review code, permissions, and credentials before use.",
        )
        if entry:
            entries.append(entry)
    return entries


def parse_appcypher(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    category = "Other"
    kind = "mcp-server"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# Tools & Utilities"):
            category = "MCP Tooling"
            kind = "mcp-tooling"
            continue
        if line.startswith("## "):
            heading = re.sub(r"<[^>]+>", "", line[3:])
            category = strip_markdown(heading).strip()
            if kind != "mcp-tooling":
                kind = "mcp-server"
            continue
        if not line.startswith("- "):
            continue
        links = list(BULLET_GITHUB_LINK.finditer(line))
        if not links:
            continue
        match = links[0]
        name, url = match.groups()
        description = description_after_project(line, match)
        entry = new_entry(
            name=name,
            url=url,
            description=description,
            kind=kind,
            category=category,
            source_id="appcypher-mcp",
            compatibility=("claude-code", "codex", "mcp"),
            official="⭐" in line,
            verification="curated-list",
            license_name="See upstream repository",
        )
        if entry:
            entries.append(entry)
    return entries


def parse_manual_research(
    root: Path, research_manifest: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    specs = (
        ("claude-native.json", "curated", "tool"),
        ("mcp-servers.json", "curated", "mcp-server"),
    )
    for filename, tier, default_kind in specs:
        path = root / "research" / filename
        if not path.exists():
            continue
        checked_at = research_manifest[filename]["checked_at"]
        payload = load_json(path)
        if isinstance(payload, dict):
            payload = payload.get("entries", [])
        for item in payload:
            url = normalize_github_url(str(item.get("url") or ""))
            if not url:
                continue
            declared_kind = str(item.get("kind") or "").lower()
            raw_kind = declared_kind or default_kind
            category = str(item.get("category") or "Community research")
            item_tags = [str(tag).lower() for tag in (item.get("tags") or ())]
            kind_haystack = " ".join([raw_kind, category.lower(), *item_tags])
            license_map = {
                "license-mit": "MIT",
                "license-apache-2-0": "Apache-2.0",
                "license-bsd-3-clause": "BSD-3-Clause",
                "license-agpl-3-0": "AGPL-3.0",
                "license-gpl-3-0": "GPL-3.0",
            }
            detected_license = next(
                (license_map[tag] for tag in item_tags if tag in license_map),
                None,
            )
            exact_license_overrides = {
                "https://github.com/hashicorp/terraform-mcp-server": (
                    "MPL-2.0",
                    True,
                ),
                "https://github.com/neo4j/mcp": ("GPL-3.0", True),
                "https://github.com/wise-vision/mcp_server_ros_2": (
                    "MPL-2.0",
                    True,
                ),
                # The current work is BUSL-1.1; EPL-2.0 is only the future
                # change license and must not be presented as open source yet.
                "https://github.com/schemacrawler/SchemaCrawler-AI": (
                    "BUSL-1.1",
                    False,
                ),
            }
            license_name, license_verified = exact_license_overrides.get(
                url,
                (detected_license or "See upstream repository", bool(detected_license)),
            )
            if url in exact_license_overrides:
                item_tags = [
                    tag for tag in item_tags if not tag.startswith("license-")
                ]
                item_tags.append(f"license-{slugify(license_name)}")
            if declared_kind in KIND_ORDER:
                kind = declared_kind
            elif default_kind == "mcp-server":
                kind = "mcp-server"
            elif "marketplace" in kind_haystack or "awesome-list" in kind_haystack:
                kind = "collection"
            elif "plugin" in kind_haystack:
                kind = "plugin"
            elif "skill" in kind_haystack:
                kind = "skill"
            elif "command" in kind_haystack:
                kind = "command"
            elif "hook" in kind_haystack:
                kind = "hook"
            elif "agent" in kind_haystack or "orchestrat" in kind_haystack:
                kind = "agent"
            elif "workflow" in kind_haystack:
                kind = "workflow"
            elif any(
                value in kind_haystack
                for value in ("client", "gui", "ide-integration", "remote-control")
            ):
                kind = "interface"
            elif any(
                value in kind_haystack
                for value in ("observability", "monitoring", "statusline")
            ):
                kind = "monitoring"
            elif any(value in kind_haystack for value in ("guide", "learning", "tutorial")):
                kind = "learning"
            else:
                kind = "tool"
            source_url = str(
                item.get("source_list_url")
                or item.get("source")
                or "https://github.com/topics/claude-code"
            )
            source_id = "manual-research"
            declared_compatibility = item.get("compatibility")
            if isinstance(declared_compatibility, list) and declared_compatibility:
                compatibility = tuple(str(value) for value in declared_compatibility)
            elif kind == "mcp-server":
                compatibility = ("claude-code", "codex", "mcp")
            elif kind == "skill":
                compatibility = ("agent-skills", "claude-code", "codex")
            else:
                compatibility = ("claude-code",)
            install = item.get("install")
            if install is not None:
                install = str(install)
            entry = new_entry(
                name=str(item.get("name") or url.rsplit("/", 1)[-1]),
                url=url,
                description=str(item.get("description") or ""),
                kind=kind,
                category=category,
                source_id=source_id,
                tags=item_tags,
                compatibility=compatibility,
                official=bool(item.get("official", False)),
                install=install,
                author=str(item["author"]) if item.get("author") else None,
                verification="manually-researched",
                license_name=license_name,
                notes=str(item.get("evidence_note") or ""),
                checked_at=checked_at,
            )
            if entry:
                entry["source_tier"] = tier
                entry["license_verified"] = license_verified
                entry["license_checked_at"] = checked_at if license_verified else None
                entry["sources"] = [
                    {
                        "name": "Parallel web/GitHub research",
                        "url": source_url,
                    }
                ]
                entries.append(entry)
    return entries


def write_sources_page() -> None:
    path = ROOT / "research" / "ecosystem-sources.json"
    if not path.exists():
        return
    payload = load_json(path)
    if isinstance(payload, dict):
        payload = payload.get("sources", [])
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in payload:
        grouped[str(item.get("type") or "Other")].append(item)
    checked_dates = sorted(
        {
            str(item.get("last_checked"))
            for item in payload
            if item.get("last_checked")
        }
    )
    date_summary = ", ".join(checked_dates) if checked_dates else "not recorded"
    lines = [
        "# Research sources",
        "",
        (
            f"{len(payload):,} discovery, specification, registry, licensing, and "
            f"security sources with record-level check dates ({date_summary})."
        ),
        "",
        "These pages generate leads and evidence; a directory listing is never treated as a security or license guarantee.",
        "",
    ]
    for source_type, items in sorted(grouped.items(), key=lambda pair: pair[0].lower()):
        lines.extend([f"## {source_type.replace('-', ' ').title()}", ""])
        lines.extend(
            [
                "| Source | Scope | Why it matters | Trust |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in sorted(items, key=lambda record: str(record.get("name", "")).lower()):
            def clean(value: Any) -> str:
                return str(value or "").replace("|", "\\|").replace("\n", " ")

            lines.append(
                f"| [{clean(item.get('name'))}]({item.get('url')}) "
                f"| {clean(item.get('scope'))} "
                f"| {clean(item.get('why_useful'))} "
                f"| {clean(item.get('trust_level'))} |"
            )
        lines.append("")
    (ROOT / "docs" / "SOURCES.md").write_text(
        "\n".join(lines).rstrip() + "\n", encoding="utf-8"
    )


def calculate_counts(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind = Counter(item["kind"] for item in entries)
    by_tier = Counter(item["source_tier"] for item in entries)
    by_category = Counter(item["category"] for item in entries)
    return {
        "total": len(entries),
        "official_directory": by_tier.get("official", 0),
        "official_provider": sum(item["official"] for item in entries),
        "license_verified": sum(item["license_verified"] for item in entries),
        "github_repositories": len({item["repository_url"].lower() for item in entries}),
        "by_kind": dict(sorted(by_kind.items())),
        "by_tier": dict(
            sorted(by_tier.items(), key=lambda pair: TIER_ORDER.get(pair[0], 99))
        ),
        "by_category": dict(
            sorted(by_category.items(), key=lambda pair: (-pair[1], pair[0].lower()))
        ),
    }


def latest_checked_date(entries: list[dict[str, Any]]) -> str:
    return max(
        (str(entry.get("last_checked") or CHECKED_DATE) for entry in entries),
        default=CHECKED_DATE,
    )


def write_json_catalog(entries: list[dict[str, Any]], counts: dict[str, Any]) -> None:
    payload = {
        "schema_version": "1.0.0",
        "generated_at": latest_checked_date(entries),
        "description": (
            "A source-backed catalog of open/public-source extensions for Claude Code, "
            "Codex, Agent Skills, and MCP-compatible coding agents."
        ),
        "counts": counts,
        "entries": entries,
    }
    path = ROOT / "catalog" / "catalog.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def csv_safe_cell(value: Any) -> Any:
    """Prevent spreadsheet applications from evaluating imported text as formulas."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def write_csv_catalog(entries: list[dict[str, Any]]) -> None:
    path = ROOT / "catalog" / "catalog.csv"
    fieldnames = [
        "id",
        "name",
        "aliases",
        "url",
        "repository_url",
        "description",
        "kind",
        "category",
        "source_tier",
        "official",
        "tags",
        "compatibility",
        "install",
        "install_commands",
        "author",
        "license",
        "license_verified",
        "license_checked_at",
        "verification",
        "last_checked",
        "source_urls",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for entry in entries:
            row = {key: entry.get(key) for key in fieldnames}
            row["aliases"] = ";".join(entry["aliases"])
            row["tags"] = ";".join(entry["tags"])
            row["compatibility"] = ";".join(entry["compatibility"])
            row["install_commands"] = ";".join(entry["install_commands"])
            row["source_urls"] = ";".join(source["url"] for source in entry["sources"])
            writer.writerow({key: csv_safe_cell(value) for key, value in row.items()})


def markdown_entry(entry: dict[str, Any]) -> str:
    badges: list[str] = []
    if entry["official"]:
        badges.append("official")
    badges.append(entry["source_tier"])
    metadata = f"{entry['kind']} · {entry['category']} · {', '.join(badges)}"
    commands = entry.get("install_commands") or []
    install = ""
    if commands:
        label = "Install" if len(commands) == 1 else "Installs"
        install = f" {label}: " + " · ".join(f"`{command}`" for command in commands)
    return (
        f"- [{entry['name']}]({entry['url']}) — {entry['description']} "
        f"<sub>{metadata}</sub>{install}"
    )


def write_kind_pages(entries: list[dict[str, Any]]) -> dict[str, int]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[KIND_PAGE.get(entry["kind"], "other")].append(entry)

    page_titles = {
        "plugins": "Claude Code Plugins",
        "skills-commands-hooks": "Skills, Commands & Hooks",
        "agents-workflows": "Agents & Workflows",
        "mcp-servers": "MCP Servers",
        "mcp-tooling": "MCP Frameworks, Registries & Tooling",
        "tools-interfaces": "Tools, Interfaces & Monitoring",
        "learning": "Learning & Reference",
        "collections": "Collections & Awesome Lists",
        "other": "Other Projects",
    }
    output_dir = ROOT / "catalog" / "by-kind"
    output_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    catalog_date = latest_checked_date(entries)
    for page, title in page_titles.items():
        page_entries = grouped.get(page, [])
        counts[page] = len(page_entries)
        by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in page_entries:
            by_category[entry["category"]].append(entry)
        lines = [
            f"# {title}",
            "",
            f"{len(page_entries):,} source-backed entries. Generated from `catalog/catalog.json` on {catalog_date}.",
            "",
            "> Inclusion is not an endorsement or security audit. Review upstream code, permissions, credentials, and licenses before installation.",
            "",
            "[← Back to catalog index](../../CATALOG.md)",
            "",
        ]
        for category, items in sorted(
            by_category.items(), key=lambda pair: (-len(pair[1]), pair[0].lower())
        ):
            lines.extend([f"## {category}", ""])
            lines.extend(markdown_entry(item) for item in items)
            lines.append("")
        (output_dir / f"{page}.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return counts


def write_verified_open_source_page(entries: list[dict[str, Any]]) -> int:
    """Render entries whose artifact-level open-source license was checked."""
    verified = [entry for entry in entries if entry["license_verified"]]
    license_dates = sorted(
        {
            entry["license_checked_at"]
            for entry in verified
            if entry.get("license_checked_at")
        }
    )
    date_summary = ", ".join(license_dates) if license_dates else "not recorded"
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in verified:
        by_kind[entry["kind"]].append(entry)
    lines = [
        "# License-verified open-source projects",
        "",
        (
            f"{len(verified):,} entries have artifact-level license evidence from "
            f"research passes dated {date_summary}."
        ),
        "",
        (
            "> License verification means the linked artifact had a recognized "
            "open-source license at the checked revision. It is not a security, "
            "maintenance, or compatibility endorsement."
        ),
        "",
        "[← Back to catalog index](../CATALOG.md)",
        "",
    ]
    kind_titles = {
        "mcp-server": "MCP Servers",
        "mcp-tooling": "MCP Tooling",
    }
    for kind, items in sorted(
        by_kind.items(), key=lambda pair: (KIND_ORDER.get(pair[0], 99), pair[0])
    ):
        title = kind_titles.get(kind, kind.replace("-", " ").title())
        lines.extend([f"## {title} ({len(items):,})", ""])
        by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in items:
            by_category[entry["category"]].append(entry)
        for category, category_entries in sorted(
            by_category.items(), key=lambda pair: (-len(pair[1]), pair[0].lower())
        ):
            lines.extend([f"### {category}", ""])
            for entry in category_entries:
                lines.append(
                    f"- [{entry['name']}]({entry['url']}) — "
                    f"{entry['description']} "
                    f"<sub>{entry['license']} · checked "
                    f"{entry['license_checked_at']} · {entry['source_tier']}</sub>"
                )
            lines.append("")
    (ROOT / "catalog" / "verified-open-source.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )
    return len(verified)


def write_catalog_index(
    entries: list[dict[str, Any]], counts: dict[str, Any], page_counts: dict[str, int]
) -> None:
    page_titles = {
        "plugins": "Plugins",
        "skills-commands-hooks": "Skills, commands & hooks",
        "agents-workflows": "Agents & workflows",
        "mcp-servers": "MCP servers",
        "mcp-tooling": "MCP tooling",
        "tools-interfaces": "Tools & interfaces",
        "learning": "Learning & reference",
        "collections": "Collections",
        "other": "Other",
    }
    lines = [
        "# Catalog",
        "",
        (
            f"Browse **{counts['total']:,} entries** spanning "
            f"**{counts['github_repositories']:,} GitHub repositories**. "
            "The JSON and CSV files are the canonical datasets; these pages are generated views."
        ),
        "",
        "| View | Entries |",
        "| --- | ---: |",
    ]
    for page, title in page_titles.items():
        if page_counts.get(page):
            lines.append(
                f"| [{title}](catalog/by-kind/{page}.md) | {page_counts[page]:,} |"
            )
    lines.extend(
        [
            "",
            "## License-verified view",
            "",
            (
                f"[Browse {counts['license_verified']:,} entries with artifact-level "
                "open-source license evidence](catalog/verified-open-source.md). "
                "The larger catalog keeps license status explicit rather than treating "
                "public source as automatic permission to reuse."
            ),
            "",
            "## Trust tiers",
            "",
            "| Tier | Meaning | Count |",
            "| --- | --- | ---: |",
            f"| Official | Listed in Anthropic's official Claude Code plugin directory. | {counts['by_tier'].get('official', 0):,} |",
            f"| Popular | Listed by a source whose snapshot required 1,000+ GitHub stars. | {counts['by_tier'].get('popular', 0):,} |",
            f"| Curated | Selected by a focused community list or manual research pass. | {counts['by_tier'].get('curated', 0):,} |",
            f"| Community | Included in a large community-maintained MCP index. | {counts['by_tier'].get('community', 0):,} |",
            "",
            f"**{counts['license_verified']:,} entries currently have artifact-level license evidence.** "
            "All other records remain explicitly unverified.",
            "",
            "A tier describes provenance, not safety. See [Methodology](docs/METHODOLOGY.md).",
            "",
            "## Machine-readable data",
            "",
            "- [`catalog/catalog.json`](catalog/catalog.json) — canonical structured catalog.",
            "- [`catalog/catalog.csv`](catalog/catalog.csv) — spreadsheet-friendly export.",
            "- [`catalog/schema.json`](catalog/schema.json) — JSON Schema.",
            "- [`catalog/stats.json`](catalog/stats.json) — generated aggregate counts.",
            "- [`catalog/link-overrides.json`](catalog/link-overrides.json) — reviewed canonical URL replacements and exclusions.",
            "- [`catalog/exclusions.json`](catalog/exclusions.json) — temporarily excluded dead or unsafe links with review dates.",
            "",
        ]
    )
    (ROOT / "CATALOG.md").write_text("\n".join(lines), encoding="utf-8")


def update_readme_stats(counts: dict[str, Any]) -> None:
    path = ROOT / "README.md"
    if not path.exists():
        return
    readme = path.read_text(encoding="utf-8")
    start = "<!-- catalog-stats:start -->"
    end = "<!-- catalog-stats:end -->"
    block = "\n".join(
        [
            start,
            (
                f"**{counts['total']:,} entries** · "
                f"**{counts['github_repositories']:,} GitHub repositories** · "
                f"**{counts['by_kind'].get('plugin', 0):,} plugins** · "
                f"**{counts['by_kind'].get('mcp-server', 0):,} MCP servers** · "
                f"**{counts['by_tier'].get('official', 0):,} official-directory entries**"
            ),
            end,
        ]
    )
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if pattern.search(readme):
        readme = pattern.sub(block, readme)
    else:
        readme += "\n\n" + block + "\n"
    path.write_text(readme, encoding="utf-8")


def build(source_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validate_source_manifest(source_dir)
    parsers = (
        ("anthropic-marketplace.json", parse_anthropic_marketplace),
        ("subinium-awesome.md.txt", parse_subinium),
        ("punkpeye-mcp.md.txt", parse_punkpeye),
        ("appcypher-mcp.md.txt", parse_appcypher),
    )
    raw_entries: list[dict[str, Any]] = []
    for filename, parser in parsers:
        path = source_dir / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Missing upstream snapshot: {path}. Run scripts/fetch_sources.py first."
            )
        parsed = parser(path)
        print(f"{filename}: {len(parsed):,} parsed")
        raw_entries.extend(parsed)
    research_manifest = load_research_manifest()
    manual = parse_manual_research(ROOT, research_manifest)
    if manual:
        print(f"manual research: {len(manual):,} parsed")
        raw_entries.extend(manual)
    overrides = load_link_overrides()
    raw_entries = apply_link_overrides(raw_entries, overrides)
    write_exclusions(overrides)
    entries = merge_entries(raw_entries)
    counts = calculate_counts(entries)
    return entries, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Directory containing fetched upstream snapshots.",
    )
    args = parser.parse_args()
    entries, counts = build(args.source_dir)
    (ROOT / "catalog").mkdir(parents=True, exist_ok=True)
    write_json_catalog(entries, counts)
    write_csv_catalog(entries)
    (ROOT / "catalog" / "stats.json").write_text(
        json.dumps(counts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    page_counts = write_kind_pages(entries)
    write_verified_open_source_page(entries)
    write_catalog_index(entries, counts, page_counts)
    write_sources_page()
    update_readme_stats(counts)
    print(
        f"Built {counts['total']:,} entries across "
        f"{counts['github_repositories']:,} GitHub repositories."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
