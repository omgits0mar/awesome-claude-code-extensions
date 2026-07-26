# MCP research sources

Snapshot date: 2026-07-26

## Primary sources consulted

- [Docker MCP Registry](https://github.com/docker/mcp-registry) — the main curated source. Its current registry metadata supplied canonical source repositories, descriptions, categories, tags, and commit pins.
- [Docker MCP Registry contribution policy](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md) — states that submitted servers need a license that permits consumption and describes CI and Docker-team review.
- [Docker MCP Registry quality standards](https://github.com/docker/mcp-registry#-compliance-and-quality-standards) — documents the registry's requirements for security practices, documentation, Docker deployment, MCP compatibility, and error handling.
- [Official Model Context Protocol Registry](https://github.com/modelcontextprotocol/registry) and its [live API documentation](https://registry.modelcontextprotocol.io/docs) — consulted to confirm the official registry model, publication metadata, and namespace ownership checks.
- [GitHub repository search API: `topic:mcp-server`, sorted by stars](https://api.github.com/search/repositories?q=topic%3Amcp-server&sort=stars&order=desc&per_page=100&page=1) — supplied the popularity complement, declared SPDX licenses, star counts, descriptions, and update timestamps; pages 1–3 were inspected.
- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers) — consulted for ecosystem breadth, category vocabulary, and an independent cross-check of project URLs.
- [MCP Reference Servers](https://github.com/modelcontextprotocol/servers) — consulted for the official reference implementations and the archived-server status noted in the catalog.

## Selection and normalization

- Total: **228 distinct open-source GitHub projects**.
- Base set: 176 unique source repositories from Docker's curated MCP Registry, deduplicated because some monorepositories publish several servers.
- License audit: common license files and README license notices were fetched at each Docker-registry-pinned revision; 23 registry source repositories without recognized open-license evidence were excluded.
- Popularity complement: 52 additional MCP projects from GitHub's star-sorted `mcp-server` topic results; only entries with an explicit SPDX license were retained.
- Canonicalization: GitHub URLs were reduced to `https://github.com/owner/repo`, trailing slashes and `.git` were removed, and deduplication was case-insensitive.
- Descriptions were rewritten into neutral, one-sentence capability summaries based on registry or repository metadata.
- Categories and tags are editorial normalization for navigation; they do not imply endorsement.

### Category coverage

- Browser Automation: 7
- Cloud & DevOps: 16
- Commerce & Marketing: 8
- Communication: 4
- Data & AI: 16
- Databases: 24
- Developer Tools: 38
- Finance: 12
- Games & Creative: 3
- Healthcare & Bio: 2
- Integration & Orchestration: 4
- IoT & Hardware: 2
- Knowledge & Memory: 8
- Monitoring & Observability: 10
- Productivity: 20
- Research & Education: 5
- Security: 20
- Travel & Maps: 5
- Web & Search: 24

## Caveats

- This is a point-in-time research snapshot, not an exhaustive index; stars, licenses, ownership, maintenance status, and repository availability can change.
- A recognized license text or declared SPDX identifier is a strong screening signal, not a substitute for legal review of the full current license and repository history.
- Some repositories bundle MCP support inside a broader application or contain multiple MCP servers; these are intentionally included as Claude Code-usable integrations.
- The archived MCP reference-server repository is retained for historical and implementation value and is tagged `archived`; prefer maintained replacements for production use.
- Compatibility with MCP does not make every tool safe to grant broad credentials or filesystem/network access; use least-privilege configuration and pin reviewed versions.
