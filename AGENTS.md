# Repository Guidelines

## Project Structure & Module Organization

- `scripts/` contains the Python catalog pipeline: source parsing, normalization, generation, validation, discovery, and link checking.
- `tests/` contains standard-library `unittest` coverage for parsers, URL normalization, merging, CSV safety, and link handling.
- `research/` holds reviewed source datasets and checksummed upstream snapshots. Treat snapshots as immutable inputs unless intentionally refreshing them.
- `catalog/` and `CATALOG.md` are generated outputs, including JSON, CSV, statistics, schema, and per-kind indexes.
- `docs/` documents methodology, taxonomy, sources, licensing, and safety. GitHub workflows and issue forms live under `.github/`.

## Build, Test, and Development Commands

Use Python 3.10 or newer; runtime code uses only the standard library.

```bash
make test               # Run all test_*.py files.
make build              # Regenerate catalog files from committed inputs.
make validate           # Check schema, counts, generated views, and invariants.
make all                # Test, build, then validate.
make check-links        # Check a deterministic 250-link network sample.
make refresh-snapshots  # Fetch upstream inputs; review every resulting diff.
```

After changing research data or parsers, run `make all` and commit the regenerated outputs. CI rejects stale generated files.

## Coding Style & Naming Conventions

Follow conventional Python style: four-space indentation, `snake_case` functions and variables, `PascalCase` test classes, and uppercase module constants. Prefer type hints, `pathlib.Path`, small pure helpers, deterministic ordering, and standard-library dependencies. Keep catalog descriptions neutral, factual, original, and no longer than the schema permits. Do not hand-edit generated catalog views.

## Testing Guidelines

Add focused regression tests in `tests/test_<area>.py` for parser, normalization, deduplication, safety, or schema changes. Use descriptive `test_<behavior>` methods. There is no numeric coverage threshold; changed behavior must be exercised directly. Run both `make test` and `make validate` before submitting.

## Commit & Pull Request Guidelines

The current history uses concise, imperative, sentence-style subjects, for example `Initial catalog of Claude Code extensions`. Keep each commit to one logical change. Pull requests should explain the change, cite source evidence, link related issues, disclose security-relevant behavior, and list validation commands run. Data changes must include generated JSON, CSV, statistics, and Markdown views.

## Security & Data Integrity

Never commit tokens or credentials; pass `GH_TOKEN` through the environment. Treat third-party repositories and snapshots as untrusted. Verify canonical URLs, artifact-level license evidence, installation documentation, and high-impact hooks or shell behavior before promoting an entry.
