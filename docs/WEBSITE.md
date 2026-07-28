# Website

The searchable Claude Code and Codex catalog is a dependency-free static site in `site/`. It follows the same generated-data rule as the rest of the repository: the browser reads `catalog/catalog.json`; frontend files do not duplicate or hand-edit catalog records.

## Data flow

1. `make all` tests, rebuilds, and validates the canonical catalog.
2. `.github/workflows/pages.yml` copies the site and generated JSON/CSV into a GitHub Pages artifact.
3. `scripts/fetch_github_metadata.py` uses the workflow's short-lived `GITHUB_TOKEN` to fetch repository-level stars, activity, license signals, and owner avatars in GraphQL batches.
4. The browser joins that dated metadata to catalog entries by `repository_url`.

Stars stay outside the catalog schema because they change continuously. The interface labels them as dated discovery signals, never as security or quality scores. Multiple extensions from one repository share one metadata record.

The “Works with” filter reads each entry’s evidence-backed `compatibility` values. Portable Agent Skills and MCP servers can appear for both Claude Code and Codex, while client-native artifacts stay scoped to their documented host.

Repository icons use the GitHub owner avatar returned by the metadata build, with a deterministic initials tile when no avatar is available. Arbitrary README images are not scraped or hotlinked: those assets can be badges, screenshots, or third-party trademarks and need separate provenance review.

## Local preview

Stage the site into a temporary directory so its relative production paths remain accurate:

```bash
preview_dir="$(mktemp -d)"
mkdir -p "$preview_dir/catalog"
cp -R site/. "$preview_dir/"
cp catalog/catalog.json catalog/catalog.csv catalog/stats.json "$preview_dir/catalog/"
python3 scripts/fetch_github_metadata.py --allow-empty --output "$preview_dir/github-metadata.json"
python3 -m http.server 8000 --directory "$preview_dir"
```

Open `http://localhost:8000/`. Star filtering is disabled in an unauthenticated local preview. To include live metadata, provide `GH_TOKEN` or `GITHUB_TOKEN` when running the metadata command.

## GitHub Pages setup

In the repository settings, choose **Pages → Build and deployment → Source: GitHub Actions**. Pushes to `main`, manual runs, and the weekly schedule then deploy the static artifact. The workflow needs only read access to repository contents plus the standard `pages: write` and `id-token: write` deployment permissions.
