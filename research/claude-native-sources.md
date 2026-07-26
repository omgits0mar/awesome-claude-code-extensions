# Claude Code-native catalog sources

Research date: 2026-07-26

This catalog uses GitHub repository or repository-subpath URLs as canonical project identifiers and deduplicates them case-insensitively after removing `.git` and trailing slashes.

- Catalog size: **453 distinct GitHub repository or project-subpath entries**.
- URL validation: **453/453 targets returned HTTP 200** on 2026-07-26 (one transient timeout succeeded on immediate retry).

## Primary and authoritative sources

- [Anthropic Claude Code repository](https://github.com/anthropics/claude-code) — official implementation, bundled plugin examples, plugin-development skills, hooks, commands, and SDK references.
- [Anthropic official plugin directory](https://github.com/anthropics/claude-plugins-official) — Anthropic-managed Claude Code marketplace.
- [Anthropic official marketplace manifest](https://github.com/anthropics/claude-plugins-official/blob/main/.claude-plugin/marketplace.json) — machine-readable plugin names, descriptions, sources, repository subpaths, refs, and pinned SHAs; used to enumerate native plugins.
- [Anthropic Agent Skills](https://github.com/anthropics/skills) — official Agent Skills examples, specification, templates, and Claude Code marketplace instructions.
- [Claude Code plugin discovery documentation](https://code.claude.com/docs/en/discover-plugins) — official installation and marketplace-discovery behavior.
- [Claude Code marketplace documentation](https://code.claude.com/docs/en/plugin-marketplaces) — official marketplace schema and distribution guidance.

## Curated discovery indexes

- [jqueryscript/awesome-claude-code](https://github.com/jqueryscript/awesome-claude-code/blob/main/README.md) — broad, category-structured index used for popular skills, agents, plugins, tools, IDE integrations, clients, statuslines, observability, SDKs, and examples.
- [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code/blob/main/README.md) — hand-curated index used as a quality-oriented cross-check and source of newer or more specialized projects.
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) — large installable subagent collection and Claude Code marketplace.
- [wshobson/agents](https://github.com/wshobson/agents) — production-oriented subagent, skill, command, and plugin marketplace.

## Marketplace repositories inspected

- [daymade/claude-code-skills](https://github.com/daymade/claude-code-skills)
- [EricGrill/agents-skills-plugins](https://github.com/EricGrill/agents-skills-plugins)
- [netresearch/claude-code-marketplace](https://github.com/netresearch/claude-code-marketplace)
- [mhattingpete/claude-skills-marketplace](https://github.com/mhattingpete/claude-skills-marketplace)
- [duyet/claude-plugins](https://github.com/duyet/claude-plugins)
- [hyperskill/claude-code-marketplace](https://github.com/hyperskill/claude-code-marketplace)
- [dashed/claude-marketplace](https://github.com/dashed/claude-marketplace)
- [danielrosehill/Claude-Code-Plugins](https://github.com/danielrosehill/Claude-Code-Plugins)
- [microsoft/power-platform-skills](https://github.com/microsoft/power-platform-skills)
- [matlab/skills](https://github.com/matlab/skills)
- [jeremylongshore/claude-code-plugins-plus-skills](https://github.com/jeremylongshore/claude-code-plugins-plus-skills)
- [xiaolai/claude-plugin-marketplace](https://github.com/xiaolai/claude-plugin-marketplace)

## Scope and caveats

- Inclusion means a project was present in an official manifest, documented itself as Claude Code-compatible, or appeared in a maintained Claude Code-specific curated index; it is not a security endorsement.
- Anthropic's official directory includes both Anthropic-maintained and third-party plugins, and Anthropic explicitly advises users to review third-party plugin code and permissions.
- Popularity changes quickly, so star ordering from curated indexes is discovery metadata rather than a permanent ranking.
- Some projects support several coding agents in addition to Claude Code; they are included only when their README or curated evidence explicitly describes Claude Code support.
- Repository availability was checked during research, but projects can move, archive, or change licensing after the research date.
