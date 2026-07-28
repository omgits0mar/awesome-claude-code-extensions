<div align="center">

# Awesome Claude Code & Codex Extensions

[![Awesome](https://awesome.re/badge.svg)](https://awesome.re)
[![Catalog validation](https://github.com/omgits0mar/awesome-claude-code-extensions/actions/workflows/validate.yml/badge.svg)](https://github.com/omgits0mar/awesome-claude-code-extensions/actions/workflows/validate.yml)
[![Catalog: CC0](https://img.shields.io/badge/catalog-CC0--1.0-blue.svg)](LICENSE)
[![Code: MIT](https://img.shields.io/badge/code-MIT-green.svg)](LICENSE-CODE)

A large, source-backed index of extensions for Claude Code and Codex: plugins, Agent Skills, agents, commands, hooks, workflows, MCP servers, interfaces, and supporting tools.

<!-- catalog-stats:start -->
**2,465 entries** · **2,382 GitHub repositories** · **311 plugins** · **1,643 MCP servers** · **268 official-directory entries**
<!-- catalog-stats:end -->

## [🔎 Open the searchable web catalog →](https://omgits0mar.github.io/awesome-claude-code-extensions/)

Filter by **Claude Code or Codex compatibility**, artifact type, GitHub stars, category, provenance, and verified license evidence.

[Browse as Markdown](CATALOG.md) · [License-verified](catalog/verified-open-source.md) · [JSON](catalog/catalog.json) · [CSV](catalog/catalog.csv) · [Add a project](https://github.com/omgits0mar/awesome-claude-code-extensions/issues/new?template=add-project.yml) · [Contribution guide](CONTRIBUTING.md) · [Methodology](docs/METHODOLOGY.md)

</div>

## Search on the web

The [interactive catalog](https://omgits0mar.github.io/awesome-claude-code-extensions/) searches every entry in the generated dataset and filters by supported client, artifact type, provenance tier, category, current GitHub stars, first-party status, and verified license evidence. It is a dependency-free static site hosted with GitHub Pages; repository stars and avatars are refreshed during deployment without changing the deterministic catalog.

See [Website architecture and local preview](docs/WEBSITE.md) for implementation and deployment details.

## Start here

The catalog is split by artifact type so a collection with hundreds of plugins is not confused with one plugin, and an MCP registry is not mislabeled as an MCP server.

| You want to… | Browse |
| --- | --- |
| Browse only entries with checked open-source license evidence | [License-verified projects](catalog/verified-open-source.md) |
| Add installable Claude Code capabilities | [Claude Code plugins](catalog/by-kind/plugins.md) |
| Reuse portable workflows in Claude Code or Codex | [Skills, commands & hooks](catalog/by-kind/skills-commands-hooks.md) |
| Coordinate specialist agents or development processes | [Agents & workflows](catalog/by-kind/agents-workflows.md) |
| Connect Claude Code or Codex to external tools and data | [MCP servers](catalog/by-kind/mcp-servers.md) |
| Build, route, inspect, or secure MCP integrations | [MCP tooling](catalog/by-kind/mcp-tooling.md) |
| Use a GUI, status line, monitor, or companion tool | [Tools & interfaces](catalog/by-kind/tools-interfaces.md) |
| Learn patterns and find other maintained indexes | [Learning](catalog/by-kind/learning.md) · [Collections](catalog/by-kind/collections.md) |

## A few strong starting points

These are recognizable, broadly useful projects—not a universal ranking:

- [Anthropic’s official plugin directory](https://github.com/anthropics/claude-plugins-official) — The canonical marketplace for official-listed Claude Code plugins.
- [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) — A broad set of agents, skills, hooks, commands, rules, and MCP configurations.
- [SuperClaude Framework](https://github.com/SuperClaude-Org/SuperClaude_Framework) — A structured command, agent, and behavioral-mode framework.
- [Claude Code Templates](https://github.com/davila7/claude-code-templates) — A CLI and web catalog for installing agents, commands, hooks, and MCP configurations.
- [Superpowers](https://github.com/obra/superpowers) — A spec, planning, TDD, and subagent execution workflow.
- [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin) — A plan, work, review, and compound loop with worktrees and multi-agent review.
- [Get Shit Done](https://github.com/gsd-build/get-shit-done) — Context-engineering and spec-driven development workflows.
- [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) — Multi-agent orchestration with automatic parallelization.
- [Claude Mem](https://github.com/thedotmack/claude-mem) — Session-history capture, compression, and context reinjection.
- [Claude HUD](https://github.com/jarrodwatts/claude-hud) — A live view of context usage, tools, agents, and tasks.
- [wshobson/agents](https://github.com/wshobson/agents) — A large marketplace of specialist agents, skills, and development tools.
- [Claude Flow](https://github.com/ruvnet/claude-flow) — Multi-agent swarm orchestration and coordination.
- [GitHub MCP Server](https://github.com/github/github-mcp-server) — GitHub’s official server for repositories, issues, pull requests, and Actions.
- [Context7](https://github.com/upstash/context7) — Version-aware library documentation and code examples for agent prompts.
- [Playwright MCP](https://github.com/microsoft/playwright-mcp) — Browser automation through accessibility snapshots.
- [Serena](https://github.com/oraios/serena) — Semantic code retrieval and symbol-level editing tools.
- [Scrapling](https://github.com/D4Vinci/Scrapling) — Adaptive web extraction with a documented MCP server and portable Agent Skill.
- [delegate-skills](https://github.com/amElnagdy/delegate-skills) — Agent Skills for delegating bounded implementation work to Claude Code, Codex, and other CLI agents.

## What the trust tiers mean

- **Official** — Listed in Anthropic’s official Claude Code plugin directory.
- **Popular** — Taken from a dated source snapshot that required at least 1,000 GitHub stars.
- **Curated** — Selected by a focused community list or a manual research pass.
- **Community** — Present in a large community-maintained MCP directory.

These tiers describe provenance, not safety. Anthropic itself warns that directory inclusion does not guarantee a plugin’s behavior. Read the source, inspect automatic hooks and shell commands, use least-privilege credentials, and pin versions where possible.

## Scope and honesty

This repository aims to be broad and reproducible, but it does not claim literal completeness. GitHub search is capped and delayed; repositories move or disappear; Claude Code and Codex use overlapping but non-identical extension surfaces; one marketplace may contain hundreds of nested components; and the official MCP Registry includes both open- and closed-source services.

The main dataset therefore:

- Uses canonical GitHub repository or repository-subpath URLs.
- Keeps repository-level and component-level counts distinct.
- Deduplicates exact canonical URLs while retaining every discovery source.
- Records a verification method and the date each source snapshot was checked.
- Distinguishes public source from a verified open-source license. Entries with `license_verified: false` require an upstream license check before redistribution or production adoption.
- Treats registry or awesome-list presence as discovery evidence, never a security endorsement.

See [Methodology](docs/METHODOLOGY.md), [Taxonomy](docs/TAXONOMY.md), [Trust & Safety](docs/TRUST_AND_SAFETY.md), and [Licensing](docs/LICENSING.md).

## Rebuild the catalog

The deterministic build requires Python 3.10+ and uses only the standard library plus the committed, checksummed source snapshots:

```bash
python3 scripts/build_catalog.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/validate_catalog.py
```

To refresh the upstream snapshots, run `python3 scripts/fetch_sources.py`, review the snapshot and manifest diff, then rebuild. A failed refresh leaves the committed inputs unchanged.

Authenticated GitHub search for Claude Code and Codex artifacts and the official MCP Registry importer write to review queues; they never auto-publish candidates:

```bash
GH_TOKEN=... python3 scripts/discover_github.py
python3 scripts/import_mcp_registry.py
```

See [Contributing](CONTRIBUTING.md) before moving a candidate into the catalog.

## Attribution and license

Original catalog structure, annotations, and prose are released under [CC0-1.0](LICENSE); repository scripts and workflows are under the [MIT License](LICENSE-CODE). Imported names, URLs, source snapshots, and descriptions sourced or normalized from upstream are excluded from that CC0 dedication and retain their upstream terms. See [NOTICE](NOTICE.md) and [third-party notices](THIRD_PARTY_NOTICES.md).

This is a community project and is not affiliated with or endorsed by Anthropic or OpenAI.
