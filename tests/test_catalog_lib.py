from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from catalog_lib import (  # noqa: E402
    concise_description,
    direct_tree_url,
    merge_entries,
    new_entry,
    normalize_github_url,
)


class UrlNormalizationTests(unittest.TestCase):
    def test_normalizes_repository_clone_url(self) -> None:
        self.assertEqual(
            normalize_github_url("http://github.com/Owner/Repo.git/"),
            "https://github.com/Owner/Repo",
        )

    def test_preserves_meaningful_component_subpath(self) -> None:
        self.assertEqual(
            normalize_github_url("https://github.com/Owner/Repo/tree/main/plugin"),
            "https://github.com/Owner/Repo/tree/main/plugin",
        )

    def test_collapses_default_branch_without_component_path(self) -> None:
        self.assertEqual(
            normalize_github_url(
                "https://github.com/stripe/agent-toolkit/tree/main"
            ),
            "https://github.com/stripe/agent-toolkit",
        )

    def test_preserves_dot_directories(self) -> None:
        self.assertEqual(
            direct_tree_url(
                "https://github.com/microsoft/Dataverse-skills.git",
                "main",
                ".github/plugins/dataverse",
            ),
            (
                "https://github.com/microsoft/Dataverse-skills/"
                "tree/main/.github/plugins/dataverse"
            ),
        )


class DescriptionTests(unittest.TestCase):
    def test_plain_text_and_length(self) -> None:
        description = concise_description(
            "[Project](https://example.com) **does useful work**. "
            + "Extra marketing text " * 50
        )
        self.assertEqual(description, "Project does useful work.")
        self.assertLessEqual(len(description), 320)

    def test_never_exceeds_requested_limit(self) -> None:
        description = concise_description("x" * 500, max_length=320)
        self.assertEqual(len(description), 320)
        self.assertTrue(description.endswith("…"))


class MergeTests(unittest.TestCase):
    def test_keeps_best_tier_and_verified_license(self) -> None:
        official = new_entry(
            name="Example",
            url="https://github.com/example/project",
            description="Example project for testing the catalog.",
            kind="plugin",
            category="Development",
            source_id="anthropic-marketplace",
        )
        curated = new_entry(
            name="Example",
            url="https://github.com/Example/Project/",
            description="A second description for the same project.",
            kind="plugin",
            category="Development",
            source_id="appcypher-mcp",
            license_name="MIT",
        )
        assert official and curated
        curated["license_verified"] = True
        curated["license_checked_at"] = "2026-07-26"
        merged = merge_entries([curated, official])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["source_tier"], "official")
        self.assertTrue(merged[0]["license_verified"])
        self.assertEqual(merged[0]["license"], "MIT")
        self.assertEqual(merged[0]["license_checked_at"], "2026-07-26")
        self.assertEqual(len(merged[0]["sources"]), 2)


if __name__ == "__main__":
    unittest.main()
