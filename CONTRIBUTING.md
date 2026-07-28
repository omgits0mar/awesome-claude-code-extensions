# Contributing

Thank you for helping make Claude Code and Codex extension discovery less fragmented.

## Add a project

The fastest route is the **[Add a project issue form](https://github.com/omgits0mar/awesome-claude-code-extensions/issues/new?template=add-project.yml)**. It asks for the repository, artifact kind, supported clients, license, install evidence, and security-relevant behavior.

A pull request is welcome when you can supply the reviewed source record and generated catalog changes described below.

An entry must:

1. Link to the canonical public GitHub repository or the exact repository subpath containing the artifact.
2. Show explicit Claude Code or Codex compatibility, a portable Agent Skills layout, or a standard MCP transport usable by one of those clients.
3. Have a license that covers the linked artifact. Public GitHub source without a license is not automatically open source.
4. Include usable installation or configuration documentation.
5. Have a neutral, original, one-sentence description of what it adds.
6. Disclose high-impact behavior such as automatic hooks, shell execution, bundled binaries, external downloads, broad credentials, or destructive tools.
7. Avoid malware, credential theft, obfuscated installers, unresolved critical compromise, or misleading claims.

We do not accept affiliate-only links, unexplained forks, scraped mirrors, link shorteners, or pay-for-placement submissions.

## Compatibility evidence

Use only the values supported by [`catalog/schema.json`](catalog/schema.json):

| Value | Evidence to provide |
| --- | --- |
| `claude-code` | Upstream Claude Code install docs, a Claude plugin/marketplace manifest, a `.claude` component path, or explicit tested support. |
| `codex` | Upstream Codex install or configuration docs, a Codex skill/plugin path, or explicit tested support. |
| `agent-skills` | A portable `SKILL.md` package following the Agent Skills layout. |
| `mcp` | A documented MCP server transport and configuration. |

Portable Agent Skills and standards-compliant MCP servers can list both Claude Code and Codex. Do not mark Claude-native plugins, hooks, commands, status lines, or interfaces as Codex-compatible without separate upstream evidence.

## Pull request workflow

1. Fork the repository and create a focused branch.
2. Add the reviewed record to [`research/claude-native.json`](research/claude-native.json). Use exact component subpaths when a repository contains independently installable artifacts. Add a new discovery source to [`research/ecosystem-sources.json`](research/ecosystem-sources.json) only when it is useful beyond one project.
3. Update the changed dataset’s `checked_at` date and SHA-256 in [`research/manifest.json`](research/manifest.json):

   ```bash
   # macOS
   shasum -a 256 research/claude-native.json research/ecosystem-sources.json

   # Linux
   sha256sum research/claude-native.json research/ecosystem-sources.json
   ```

4. Run `make all`. The build regenerates JSON, CSV, statistics, Markdown indexes, source documentation, and README counts.
5. Review every generated diff, then open a pull request using the checklist below.

Do not hand-edit `catalog/catalog.json`, `catalog/catalog.csv`, `catalog/stats.json`, `catalog/by-kind/`, `catalog/verified-open-source.md`, `CATALOG.md`, or `docs/SOURCES.md`.

### Source record example

```json
{
  "name": "Example Agent Skill",
  "url": "https://github.com/owner/repository/tree/main/skills/example",
  "description": "Portable Agent Skill for a specific, clearly described workflow.",
  "kind": "skill",
  "category": "developer-tools",
  "tags": ["agent-skills", "claude-code", "codex", "license-mit"],
  "compatibility": ["agent-skills", "claude-code", "codex"],
  "install": "npx skills add owner/repository --skill example",
  "author": "owner",
  "source_list_url": "https://github.com/owner/repository",
  "evidence_note": "The linked SKILL.md, install section, and MIT license were checked. The package runs a local helper script that writes only inside the workspace."
}
```

Use a recognized `license-*` tag only after checking that the license covers the exact linked artifact. Describe shell execution, network access, credentials, hooks, downloads, browser control, and destructive capabilities in `evidence_note`.

## Data fields

The canonical format is defined in [`catalog/schema.json`](catalog/schema.json). Important fields include:

- `url`: Exact canonical GitHub URL. Repository subpaths are allowed for independently installable components.
- `repository_url`: Root `https://github.com/owner/repo` URL.
- `kind`: Packaging or artifact type—not a marketing category.
- `category`: What the project helps a user do.
- `source_tier`: Provenance tier. Contributors generally use `curated`; maintainers assign `official` or `popular` only from recorded evidence.
- `license`, `license_verified`, and `license_checked_at`: The upstream artifact’s license status and the date its evidence was checked.
- `verification`: How relevance and availability were checked.
- `sources`: Discovery provenance, even when it differs from the canonical link.
- `compatibility`: Supported client or open-standard surfaces, backed by upstream evidence.

Do not copy upstream marketing paragraphs. Write a concise factual summary in your own words.

## Local checks

Use Python 3.10 or newer.

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/build_catalog.py
python3 scripts/validate_catalog.py
```

For a network sample:

```bash
python3 scripts/check_links.py --limit 100
```

The catalog, CSV, statistics, source documentation, README counts, and category pages are generated. Commit those outputs with any source-data change.

## Pull request checklist

- [ ] The canonical repository or exact component path is linked.
- [ ] Claude Code, Codex, Agent Skills, or MCP compatibility has upstream evidence.
- [ ] The license covers the linked artifact and its check date is recorded.
- [ ] Installation or configuration instructions are usable.
- [ ] The description is neutral, original, factual, and one sentence.
- [ ] High-impact behavior and required credentials are disclosed.
- [ ] `make all` passes and every generated file is committed.

## Review states

- **Verified** means the canonical source, license, install documentation, structure, and basic safety triage were checked at a recorded revision.
- **Community-listed** means relevance is established but deeper install or security review is pending.
- **Archived/security hold** entries live outside the main list with a clear reason.

No badge means “safe.” Reviewers communicate facts such as official source, license verified, manifest valid, install checked, automatic hooks, shell execution, network access, and credentials required.

## Corrections and removals

Open an issue for a moved repository, stale description, license change, broken installation, duplicate, maintained fork, removal request, or successor project. For sensitive security reports, follow [`SECURITY.md`](SECURITY.md).
