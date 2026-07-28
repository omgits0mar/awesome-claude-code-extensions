# Ecosystem research notes

Checked: 2026-07-26

> This is the initial design and risk-analysis record, not the current repository contract. The implemented catalog keeps a broad public-source discovery index with explicit license status and provides a separate strict [license-verified view](../catalog/verified-open-source.md).

## Recommended positioning

Build this as a curated, source-linked catalog with a reproducible discovery pipeline, not as a mirror of other projects and not as a raw dump of search results. The useful promise is:

> Open-source extensions that work with Claude Code or Codex, classified by what they add, verified against their upstream repository, and kept current with transparent freshness and safety signals.

“Public on GitHub” is not the same as “open source.” A repository without a license grants no general right to copy, modify, or redistribute its contents. The implemented repository therefore labels inherited records as unverified and separates entries with dated open-source license evidence into a strict view; it does not imply that every discovery record is reusable.

The official Claude plugin directory is a high-trust discovery source, not a blanket open-source or security guarantee. Its own repository instructs users to check each linked plugin’s license and trustworthiness. Likewise, an MCP server being present in a registry proves discoverability, not safety, quality, or open-source status.

## Recommended repository structure

```text
awesome-claude-code/
├── README.md                         # Human-curated flagship list
├── CONTRIBUTING.md                   # Inclusion, evidence, and PR rules
├── SECURITY.md                       # Reporting malicious or compromised entries
├── CODE_OF_CONDUCT.md
├── LICENSE                           # Prefer CC0-1.0 or CC-BY-4.0 for catalog prose/data
├── LICENSE-CODE                      # Optional MIT/Apache-2.0 for crawler/validator code
├── data/
│   ├── catalog.json                  # Canonical normalized entries
│   ├── catalog.schema.json
│   ├── sources.json                  # Discovery sources and crawl policy
│   ├── aliases.json                  # Renames, redirects, and canonical identities
│   └── archived.json                 # Removed/stale entries with reason and history
├── docs/
│   ├── taxonomy.md
│   ├── inclusion-policy.md
│   ├── trust-and-safety.md
│   ├── methodology.md
│   └── licensing.md
├── scripts/
│   ├── discover/                     # API/topic/registry discovery adapters
│   ├── normalize/                    # Manifest and repository normalization
│   ├── validate/                     # Schema, links, licenses, install layout
│   └── render/                       # Generate README sections from reviewed data
├── tests/
│   ├── fixtures/
│   └── catalog/
├── research/
│   ├── ecosystem-sources.json
│   └── research-notes.md
└── .github/
    ├── ISSUE_TEMPLATE/
    │   ├── add-project.yml
    │   ├── update-project.yml
    │   ├── report-security-concern.yml
    │   └── removal-request.yml
    └── workflows/
        ├── validate-catalog.yml
        ├── check-links.yml
        └── refresh-metadata.yml
```

Keep `data/catalog.json` as the source of truth and generate repetitive README sections from it. Human review should be required before a discovered candidate moves into the main catalog. This preserves both scale and editorial quality.

## Entry model

At minimum, each entry should record:

- Stable `id`, canonical `name`, and `slug`.
- `source_url`, `homepage_url`, and optional `marketplace_url`.
- `owner`, upstream authors/maintainers, and `attribution`.
- `artifact_types`: one or more of `marketplace`, `plugin`, `skill`, `subagent`, `command`, `hook`, `mcp-server`, `lsp-server`, `output-style`, `statusline`, `rules-config`, `manager-tool`, or `workflow-harness`.
- `capability_categories`: development, code quality, testing, security, DevOps/cloud, data/database, browser/web, docs/research, design/frontend, project/product, communications/business, memory/context, orchestration, media, or domain-specific.
- `compatibility`: `claude-code-native`, `agent-skills-portable`, `mcp-compatible`, `claude-desktop`, `cowork`, and other harnesses as explicit values rather than prose.
- Install evidence: marketplace/plugin identifier, install command, minimum Claude Code version if stated, and source commit/ref checked.
- `license_spdx`, `license_scope`, `license_url`, and `license_status`.
- Repository metadata: stars, forks, open issues, `pushed_at`, latest release, archived/disabled status, and default branch.
- Component counts extracted from the repository rather than copied from marketing text.
- `security_surface`: automatic hooks, shell execution, bundled binaries/scripts, MCP tools, network access, credentials, external downloads, and broad tool grants.
- `status`: active, maintenance, stale, archived, deprecated, superseded, broken, or security-hold.
- `last_verified`, `verification_method`, and reviewer.
- `aliases`, fork/upstream relationship, and a content fingerprint for deduplication.

Do not use one flat `type` field. A marketplace can contain plugins; a plugin can contain skills, agents, commands, hooks, MCP servers, LSP servers, and output styles. Preserve that hierarchy so counts are meaningful.

## Strict license-verified view criteria

An entry belongs in the main catalog only when all required checks pass:

1. **Claude Code relevance is evidenced.** At least one of:
   - A valid Claude Code marketplace or plugin manifest.
   - A valid skill with documented Claude Code placement or installation.
   - A valid `.claude/agents`, `.claude/commands`, or supported hook configuration.
   - An MCP server with a documented Claude Code configuration or standard transport that Claude Code supports.
   - A tool whose primary documented purpose is managing or extending Claude Code.
2. **The relevant source is public and canonical.** Link to the original repository or recognized upstream, not a scraper page or an unexplained fork.
3. **The relevant artifact is open source.** Verify an OSI-approved license or another explicitly approved project policy. `NOASSERTION`, a badge without a license file, or “free to use” prose is not enough.
4. **It has usable documentation.** A reader can understand the capability, prerequisites, install method, permissions, and basic invocation.
5. **It is not merely a prompt dump.** The artifact should provide a reusable, named capability or a documented Claude Code configuration.
6. **It is not obviously abandoned or broken.** Old but stable projects can remain if install and usage still verify; age alone is not disqualifying.
7. **It has a meaningful description written for this catalog.** Summarize the actual capability in original wording; do not copy marketing copy wholesale.
8. **It passes basic safety triage.** No known malware, credential theft, obfuscated install payload, unbounded destructive hook, or unresolved critical compromise.

Optional “Notable” or “Popular” badges should require evidence such as official-directory install counts, GitHub stars, downstream usage, recent releases, or multiple independent curated sources. Record the measurement and date. Never use stars alone as a quality or security score.

## Taxonomy rules

Use two independent axes:

1. **Packaging/artifact form** answers “how is it installed or loaded?”
2. **Capability category** answers “what does it help the user do?”

Important distinctions:

- A **marketplace** is a catalog; it is not itself one plugin.
- A **plugin** is an installable bundle that may contribute several component types.
- A **skill** is a progressively loaded instruction/resource package. Claude Code follows the open Agent Skills format and adds Claude-specific fields.
- A legacy **custom command** under `.claude/commands/` still works, but official documentation now treats custom commands as merged into skills and recommends skills for richer packaging. Label such entries `legacy-compatible`, not “broken.”
- A **subagent** has an isolated agent definition/context. A skill with `context: fork` may run in a subagent but remains a skill artifact.
- An **MCP server** is protocol-compatible external tooling; it need not be Claude-specific. Do not include MCP clients, SDKs, gateways, or registries in the server section unless they also expose a server.
- A **hook** runs on lifecycle events and deserves a prominent automatic-execution risk indicator.
- Rules, CLAUDE.md templates, status lines, output styles, and manager CLIs are useful extensions but should not be mislabeled as plugins.

## Discovery and refresh strategy

Use sources in descending authority:

1. Official Anthropic directories, manifests, repositories, and documentation.
2. Official Agent Skills and MCP specifications/registries.
3. Canonical upstream repositories discovered from manifests.
4. Established curated lists.
5. GitHub topics and repository search.
6. GitHub code searches for structural artifacts.
7. Automated community directories and blogs as lead generators only.

Recommended recurring pipeline:

1. Pull structured official marketplace and registry feeds.
2. Search GitHub by exact structural paths:
   - `.claude-plugin/marketplace.json`
   - `.claude-plugin/plugin.json`
   - `SKILL.md`
   - `.claude/agents/*.md`
   - `.claude/commands/*.md`
   - `hooks/hooks.json`
   - `.mcp.json`
3. Partition searches by pushed date, stars, language, organization, and topic. GitHub search returns at most 1,000 results per query and searches a bounded repository set, so one global query cannot enumerate the ecosystem.
4. Resolve every lead to its canonical repository and default-branch commit.
5. Parse manifests and repository trees; never infer component counts from the repository name.
6. Deduplicate by canonical URL, manifest source, fork lineage, and content hashes.
7. Enrich with license, activity, release, popularity, and security-surface metadata.
8. Place new or materially changed entries into a review queue.
9. Render the README only from approved catalog records.

Use authenticated GitHub API requests, ETags/conditional requests, caching, and a queue. Respect primary and secondary rate limits. Do not collect maintainer email addresses or other unnecessary personal data.

## Quality rules

- Prefer the canonical upstream link. Keep directory links only as discovery provenance.
- Verify redirects and renames; update the canonical URL while retaining old names in `aliases.json`.
- Check all install commands in a clean fixture or validate them structurally without executing third-party code.
- Run `claude plugin validate` or equivalent schema checks on plugin/marketplace fixtures when practical.
- Validate SKILL.md name, directory name, required description, YAML, links to bundled files, and Claude-specific frontmatter separately.
- Check every nested plugin/skill license. A root repository license may not cover a subdirectory, vendored content, or a remote plugin source.
- Record the exact source commit used during verification.
- Use original, neutral, one-sentence descriptions. Attribute unique claims and do not reproduce large README sections.
- Give each entry only the categories it actually implements. Avoid tag spam.
- Collapse identical forks into one canonical entry; list a fork separately only when it has a maintained, material difference.
- Do not rank sponsors above more relevant projects. Sponsorship must never affect inclusion or trust badges.
- Treat install counts, stars, forks, and directory rankings as dated signals. Keep their source and timestamp.
- Provide a visible correction, removal, and security-reporting path.
- Keep archived entries in history rather than silently deleting them, unless continued publication creates a safety or legal issue.

## Freshness, stale, and deprecated signals

Strong signals:

- GitHub `archived: true`, repository disabled, deleted, or transferred without a working redirect.
- Marketplace or plugin validation fails on the default branch.
- Documented install command fails, package is unpublished, release asset is missing, or remote endpoint is dead.
- Official documentation explicitly marks a feature, command, transport, package, or plugin as deprecated/superseded.
- Maintainer archive notice, end-of-life notice, or a successor project named by the maintainer.
- Default branch removed or manifest source pinned to an unreachable ref/SHA.
- Open critical security advisory or demonstrated compromise without a fixed release.

Review signals, not automatic removal:

- No repository push for 180 days: mark `review-due`.
- No push for 365 days: mark `stale` unless the project is intentionally stable and still verifies.
- No release for 12 months when the project previously released regularly.
- README counts no longer match the parsed tree.
- Install docs use only deprecated npm installation for Claude Code.
- Custom commands are published only under `.claude/commands/`: label `legacy-compatible`; they remain supported.
- MCP server exposes only obsolete transports or configuration no longer accepted by Claude Code.
- Issues repeatedly report broken installation with no maintainer response.
- Repository has no security policy despite executing automatic hooks or downloading binaries. This raises review priority but is not a rejection by itself.

Activity must be interpreted by artifact type. A stable single-file skill may not need frequent commits; an MCP server tied to a changing API usually does.

## Attribution and licensing

- Store upstream project name, owner, canonical URL, authors if explicitly declared, license SPDX expression, and license URL.
- Link instead of copying. The catalog’s short descriptions should be independently written factual summaries.
- If any upstream content is vendored, preserve copyright notices, license text, NOTICE files, and attribution required by that artifact’s license.
- Do not assume the license of an awesome list covers the projects it links to.
- Do not assume a repository’s root license covers external plugins referenced by marketplace URL or git-subdir.
- Anthropic’s skills repository explicitly mixes Apache-2.0 examples with source-available document skills; capture license at artifact/subdirectory level.
- GitHub’s license API is a useful first pass, not final legal verification. Use SPDX normalization plus manual review for mixed, custom, missing, or subdirectory-specific licenses.
- Logos, product names, and badges may have trademark rules separate from source-code licenses. Prefer text links and upstream-provided badges.
- License the curated catalog prose/data explicitly, preferably CC0-1.0 for maximal reuse or CC-BY-4.0 if attribution is desired. License crawler code separately under MIT or Apache-2.0.

This is operational guidance, not legal advice.

## Key risks

### Supply-chain and prompt-injection risk

Skills and agent definitions are operational instructions. Plugins may execute hooks automatically, grant tools, start MCP servers, run shell preprocessing, download packages, or bundle binaries. A clean README or a valid manifest is not a safety review. Static checks should inspect all Markdown instructions, scripts, symlinks, binaries, package-install commands, network destinations, environment-variable access, and external downloads. Pin test fixtures to commits and never execute untrusted extensions in the catalog CI runner without isolation.

### MCP trust risk

MCP servers can expose destructive tools, retrieve untrusted content, change tool lists dynamically, and handle credentials. Registry presence is not verification. Record transport, authentication, data access, tool annotations, hosted versus local execution, source availability, and whether the provider is official. Apply the official MCP and OWASP security guidance.

### False “open source” claims

Public, free, source-available, and open source are distinct. Unknown or custom licenses can make an otherwise strong entry ineligible for the main list. Mixed-license monorepos and marketplace entries pointing to external repositories are especially easy to misclassify.

### Duplicate and inflated counts

One marketplace can list hundreds of plugins; a plugin can bundle hundreds of skills; auto-indexers may count the same artifact across forks, versions, renamed repositories, generated bundles, and mirrors. Publish both repository-level and component-level counts, with a documented deduplication method.

### Popularity bias and gaming

Stars, install counts, directory rankings, and sponsorships can be manipulated or measure different things. Use them as transparent dated signals, not as the sole ordering or inclusion rule. A small official provider integration may be more trustworthy and useful than a viral prompt pack.

### Search incompleteness

GitHub search has per-query caps, default-branch and file-size constraints, incomplete results, indexing delays, and rate limits. Topic pages are self-tagged. Community directories copy one another. The catalog can be broad and reproducible, but it cannot honestly claim literal completeness.

### Description and provenance drift

Aggregators often copy stale names, install commands, star counts, licenses, and descriptions. Always resolve to the canonical upstream and retain discovery provenance separately. Refresh manifest-derived data whenever the source commit changes.

### Legal and platform-policy risk

Bulk scraping, personal-data collection, copying README text, or redistributing code without license compliance creates avoidable risk. Prefer documented APIs and structured public manifests, cache responsibly, respect GitHub policies and registry terms, and provide removal/correction channels.

## Practical publication policy

Use three visible states:

- **Verified**: structure, canonical source, open-source license, install documentation, and basic safety triage passed at a recorded commit.
- **Community-listed**: relevant and licensed, but install or deeper review is pending.
- **Archived/unsafe**: retained outside the main list with a clear reason, successor, and last known good version when appropriate.

Avoid a generic “safe” badge. Better badges communicate verifiable facts: `official source`, `license verified`, `manifest valid`, `install checked`, `automatic hooks`, `shell execution`, `network access`, `credentials required`, and `security review date`.
