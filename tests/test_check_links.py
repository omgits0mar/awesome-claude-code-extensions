from __future__ import annotations

import sys
import unittest
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_links import SafeRedirectHandler, comparable_url  # noqa: E402


class ComparableUrlTests(unittest.TestCase):
    def test_ignores_trailing_slash_and_query(self) -> None:
        self.assertEqual(
            comparable_url("https://github.com/Owner/Repo/?tab=readme"),
            comparable_url("https://github.com/Owner/Repo"),
        )

    def test_preserves_repository_move(self) -> None:
        self.assertNotEqual(
            comparable_url("https://github.com/old-owner/project"),
            comparable_url("https://github.com/new-owner/project"),
        )


class SafeRedirectTests(unittest.TestCase):
    def test_drops_authorization_on_cross_host_redirect(self) -> None:
        request = urllib.request.Request(
            "https://github.com/example/project",
            headers={"Authorization": "Bearer secret"},
        )
        redirected = SafeRedirectHandler().redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://example.org/project",
        )
        assert redirected
        self.assertIsNone(redirected.get_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
