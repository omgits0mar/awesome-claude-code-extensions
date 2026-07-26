# Methodology

Initial manual research pass: **2026-07-26**. Current per-dataset dates are recorded in the two research manifests and on each catalog entry.

## Goal

The catalog is a broad, source-linked discovery layer for open/public-source projects that extend Claude Code directly or through the Model Context Protocol. It is built as a reproducible index, not a mirror of upstream code and not a claim that every listed project is safe.

## Source order

Research uses sources in descending authority:

1. Anthropic’s official repositories, manifests, and Claude Code documentation.
2. The official Agent Skills and MCP specifications and registries.
3. Canonical repositories referenced by those manifests.
4. Maintained, focused awesome lists.
5. GitHub topics, repository search, and structural code search.
6. Community directories and blogs as lead generators.

The checked source inventory is in [`research/ecosystem-sources.json`](../research/ecosystem-sources.json) and rendered in [`SOURCES.md`](SOURCES.md).

## Current build inputs

- Anthropic’s machine-readable official marketplace manifest.
- A popularity-filtered Claude Code repository list.
- Two maintained MCP server indexes.
- A parallel manual research pass over Claude-native projects.

Build inputs are committed under [`research/snapshots`](../research/snapshots) with source URLs, a research date, and SHA-256 checksums in its manifest. A normal build is therefore deterministic and needs no network access. The fetch script stages a complete refresh, writes nothing on a network failure, and updates the committed snapshots plus manifest only after every fetch validates. Generated records retain source provenance and per-dataset check dates.

Other lists—including sources whose licenses do not permit direct modified redistribution—are used only to discover leads. Their entries are independently checked against canonical repositories before manual research data is added.

## Normalization

- GitHub links are converted to HTTPS, `.git` and trailing slashes are removed, and duplicate URL casing is collapsed.
- Exact repository subpaths remain distinct because one monorepo can contain many independently installable plugins or skills.
- `repository_url` always identifies the owner/repository root, allowing repository-level counts without inflating them with components.
- Exact canonical URLs are merged. The most authoritative description/tier wins, while aliases, every install command, discovery sources, and tags are retained.
- Confirmed repository moves and removals are recorded in [`catalog/link-overrides.json`](../catalog/link-overrides.json). Replacements retain their discovery provenance; exclusions are rendered separately for periodic rechecking.
- Descriptions are plain text, one sentence, and capped at 320 characters.
- Records are sorted deterministically by provenance tier, artifact type, category, name, and URL.

## Verification labels

- `official-marketplace`: parsed from Anthropic’s official plugin directory.
- `popular-list`: taken from a source that required 1,000+ GitHub stars on the snapshot date.
- `curated-list`: selected by a focused human-maintained list.
- `manually-researched`: checked during the parallel research pass.
- `community-awesome-list`: taken from a broad community MCP directory.

Availability is not equivalent to safety, maintenance, or license approval.

## Inclusion and license status

The ideal main-list entry has explicit Claude Code relevance, canonical public source, usable documentation, an OSI-approved license, and basic safety triage. Large inherited community indexes do not provide artifact-level license verification, so records expose `license_verified` rather than pretending public source is automatically open source.

Unknown-license entries remain discoverable with a visible warning while license enrichment is pending. The [license-verified view](../catalog/verified-open-source.md) contains only records with dated artifact-level evidence.

## Popularity

Popularity is a dated signal, not a quality score. The `popular` tier comes from a source whose stated threshold was 1,000 GitHub stars. Star values are intentionally not copied into static descriptions because they become stale quickly. Automated metadata enrichment should retain both the measurement and timestamp.

## MCP scope

Any standards-compliant MCP server can be configured for Claude Code, so the MCP section is intentionally broad. MCP clients, SDKs, registries, gateways, and scanners are classified as `mcp-tooling` unless they also expose a server.

The official MCP Registry is not imported directly into the published catalog because it is deliberately unopinionated, permits closed-source services, and contains deleted or stale records. [`scripts/import_mcp_registry.py`](../scripts/import_mcp_registry.py) creates a review queue restricted to active records with a public GitHub repository.

## Known limits

- GitHub search caps results, searches a bounded repository set, and may lag behind the default branch.
- Community lists copy one another and can propagate stale descriptions.
- Projects can move, archive, change license, or become compromised after the check date.
- Repository roots may have mixed or subdirectory-specific licenses.
- Component counts can be inflated by forks, versions, mirrors, and nested marketplaces.
- A valid manifest proves structure, not benign behavior.

Corrections are welcome through issues and pull requests.
