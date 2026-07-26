# Contributing

Thank you for helping make Claude Code extension discovery less fragmented.

## Add a project

The fastest route is the **Add a project** issue form. A pull request is welcome when you can supply the full normalized record.

An entry must:

1. Link to the canonical public GitHub repository or the exact repository subpath containing the artifact.
2. Show explicit Claude Code compatibility, a supported Agent Skills layout, or a standard MCP transport usable by Claude Code.
3. Have a license that covers the linked artifact. Public GitHub source without a license is not automatically open source.
4. Include usable installation or configuration documentation.
5. Have a neutral, original, one-sentence description of what it adds.
6. Disclose high-impact behavior such as automatic hooks, shell execution, bundled binaries, external downloads, broad credentials, or destructive tools.
7. Avoid malware, credential theft, obfuscated installers, unresolved critical compromise, or misleading claims.

We do not accept affiliate-only links, unexplained forks, scraped mirrors, link shorteners, or pay-for-placement submissions.

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

The catalog, CSV, statistics, and category pages are generated. Commit those outputs with any source-data change.

## Review states

- **Verified** means the canonical source, license, install documentation, structure, and basic safety triage were checked at a recorded revision.
- **Community-listed** means relevance is established but deeper install or security review is pending.
- **Archived/security hold** entries live outside the main list with a clear reason.

No badge means “safe.” Reviewers communicate facts such as official source, license verified, manifest valid, install checked, automatic hooks, shell execution, network access, and credentials required.

## Corrections and removals

Open an issue for a moved repository, stale description, license change, broken installation, duplicate, maintained fork, removal request, or successor project. For sensitive security reports, follow [`SECURITY.md`](SECURITY.md).
