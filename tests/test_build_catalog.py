from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_catalog import csv_safe_cell, parse_anthropic_marketplace  # noqa: E402
from catalog_lib import merge_entries  # noqa: E402


class OfficialManifestTests(unittest.TestCase):
    def test_url_source_honors_component_path_and_sha(self) -> None:
        payload = {
            "plugins": [
                {
                    "name": "example",
                    "description": "Example plugin for parser testing.",
                    "source": {
                        "source": "url",
                        "url": "https://github.com/example/plugins.git",
                        "path": "plugins/example",
                        "sha": "abc123",
                    },
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "marketplace.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            entries = parse_anthropic_marketplace(path)
        self.assertEqual(
            entries[0]["url"],
            "https://github.com/example/plugins/tree/abc123/plugins/example",
        )

    def test_shared_source_retains_every_marketplace_install_name(self) -> None:
        payload = {
            "plugins": [
                {
                    "name": "first-name",
                    "description": "First marketplace alias for the plugin.",
                    "source": {
                        "source": "url",
                        "url": "https://github.com/example/plugin.git",
                    },
                },
                {
                    "name": "second-name",
                    "description": "Second marketplace alias for the plugin.",
                    "source": {
                        "source": "url",
                        "url": "https://github.com/example/plugin.git",
                    },
                },
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "marketplace.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            merged = merge_entries(parse_anthropic_marketplace(path))
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["aliases"], ["second-name"])
        self.assertEqual(
            merged[0]["install_commands"],
            [
                "/plugin install first-name@claude-plugins-official",
                "/plugin install second-name@claude-plugins-official",
            ],
        )


class CsvSafetyTests(unittest.TestCase):
    def test_formula_leading_text_is_escaped(self) -> None:
        self.assertEqual(csv_safe_cell("=HYPERLINK(\"bad\")"), "'=HYPERLINK(\"bad\")")
        self.assertEqual(csv_safe_cell("@SUM(A1:A2)"), "'@SUM(A1:A2)")
        self.assertEqual(csv_safe_cell("normal text"), "normal text")


if __name__ == "__main__":
    unittest.main()
