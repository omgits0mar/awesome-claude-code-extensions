from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_github_metadata import (  # noqa: E402
    RepositoryRequest,
    atomic_write_json,
    build_graphql_batch,
    build_report,
    collect_repository_requests,
    fetch_repository_metadata,
    main,
    normalize_github_repository_url,
    parse_graphql_payload,
)


class RepositoryUrlTests(unittest.TestCase):
    def test_normalizes_case_suffix_query_and_trailing_slash(self) -> None:
        repository = normalize_github_repository_url(
            "HTTP://www.GitHub.com/Owner/Project.git/?tab=readme#usage"
        )
        self.assertEqual(repository.url, "https://github.com/owner/project")
        self.assertEqual(repository.owner, "owner")
        self.assertEqual(repository.name, "project")

    def test_rejects_non_repository_github_paths(self) -> None:
        invalid_urls = [
            "https://example.com/owner/project",
            "https://github.com/owner/project/tree/main",
            "https://github.com/owner",
            "https://token@github.com/owner/project",
            "git@github.com:owner/project.git",
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    normalize_github_repository_url(url)

    def test_collects_unique_sorted_urls_and_reports_invalid_entries(self) -> None:
        catalog = {
            "entries": [
                {
                    "id": "second",
                    "repository_url": "https://github.com/Zed/Repo",
                },
                {
                    "id": "duplicate",
                    "repository_url": "https://github.com/zed/repo.git",
                },
                {
                    "id": "first",
                    "repository_url": "https://github.com/Alpha/One",
                },
                {
                    "id": "invalid",
                    "repository_url": "https://github.com/Alpha/One/issues",
                },
            ]
        }
        requests, errors = collect_repository_requests(catalog)
        self.assertEqual(
            [request.url for request in requests],
            [
                "https://github.com/alpha/one",
                "https://github.com/zed/repo",
            ],
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["entry_id"], "invalid")
        self.assertEqual(errors[0]["type"], "invalid_repository_url")


class GraphQLTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repositories = [
            RepositoryRequest(
                "https://github.com/alpha/one",
                "alpha",
                "one",
            ),
            RepositoryRequest(
                "https://github.com/bravo/two",
                "bravo",
                "two",
            ),
        ]

    def test_builds_aliased_query_with_all_required_fields(self) -> None:
        query, variables, aliases = build_graphql_batch(self.repositories)
        self.assertEqual(
            variables,
            {
                "owner0": "alpha",
                "name0": "one",
                "owner1": "bravo",
                "name1": "two",
            },
        )
        self.assertEqual(aliases["repo1"], self.repositories[1])
        for field in (
            "nameWithOwner",
            "url",
            "stargazerCount",
            "forkCount",
            "isArchived",
            "isDisabled",
            "isFork",
            "pushedAt",
            "updatedAt",
            "primaryLanguage",
            "licenseInfo",
            "owner",
            "avatarUrl",
            "openGraphImageUrl",
        ):
            with self.subTest(field=field):
                self.assertIn(field, query)

    def test_preserves_partial_data_and_maps_graphql_error_to_url(self) -> None:
        _, _, aliases = build_graphql_batch(self.repositories)
        node = {
            "nameWithOwner": "Alpha/One",
            "url": "https://github.com/Alpha/One",
            "stargazerCount": 12,
            "forkCount": 3,
            "isArchived": False,
            "isDisabled": False,
            "isFork": False,
            "pushedAt": "2026-07-01T00:00:00Z",
            "updatedAt": "2026-07-02T00:00:00Z",
            "primaryLanguage": {"name": "Python", "color": "#3572A5"},
            "licenseInfo": {"spdxId": "MIT"},
            "owner": {"avatarUrl": "https://avatars.example/alpha"},
            "openGraphImageUrl": "https://images.example/alpha-one",
        }
        repositories, errors = parse_graphql_payload(
            {
                "data": {"repo0": node, "repo1": None},
                "errors": [
                    {
                        "message": "Could not resolve to a Repository",
                        "path": ["repo1"],
                    }
                ],
            },
            aliases,
        )
        self.assertEqual(
            list(repositories),
            ["https://github.com/alpha/one"],
        )
        self.assertEqual(repositories["https://github.com/alpha/one"]["forkCount"], 3)
        self.assertEqual(len(errors), 1)
        self.assertEqual(
            errors[0]["repository_url"],
            "https://github.com/bravo/two",
        )
        self.assertEqual(errors[0]["type"], "graphql")

    def test_continues_after_failed_batch(self) -> None:
        calls = 0

        def fake_request(
            query: str,
            variables: dict[str, str],
            token: str,
        ) -> dict[str, object]:
            nonlocal calls
            calls += 1
            self.assertEqual(token, "secret")
            if calls == 1:
                raise RuntimeError("temporary failure")
            return {
                "data": {
                    "repo0": {
                        "nameWithOwner": "Bravo/Two",
                        "url": "https://github.com/Bravo/Two",
                        "stargazerCount": 5,
                    }
                }
            }

        repositories, errors = fetch_repository_metadata(
            self.repositories,
            "secret",
            batch_size=1,
            request_fn=fake_request,
        )
        self.assertEqual(calls, 2)
        self.assertNotIn("https://github.com/alpha/one", repositories)
        self.assertIn("https://github.com/bravo/two", repositories)
        self.assertEqual(errors[0]["type"], "request")
        self.assertEqual(
            errors[0]["repository_urls"],
            ["https://github.com/alpha/one"],
        )


class ReportAndCliTests(unittest.TestCase):
    def test_build_report_has_deterministic_keys_and_counts(self) -> None:
        requests = [
            RepositoryRequest("https://github.com/b/two", "b", "two"),
            RepositoryRequest("https://github.com/a/one", "a", "one"),
        ]
        report = build_report(
            catalog_entry_count=3,
            requests=requests,
            repositories={
                "https://github.com/b/two": {"stargazerCount": 2},
                "https://github.com/a/one": {"stargazerCount": 1},
            },
            errors=[
                {
                    "type": "invalid_repository_url",
                    "entry_index": 2,
                    "message": "bad",
                }
            ],
            generated_at="2026-07-26T00:00:00Z",
        )
        self.assertEqual(
            list(report["repositories"]),
            [
                "https://github.com/a/one",
                "https://github.com/b/two",
            ],
        )
        self.assertEqual(
            report["counts"],
            {
                "catalog_entries": 3,
                "requested": 2,
                "fetched": 2,
                "failed": 0,
                "invalid": 1,
                "errors": 1,
            },
        )

    def test_atomic_write_replaces_destination_with_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "nested" / "metadata.json"
            atomic_write_json(output, {"z": 1, "a": 2})
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8")),
                {"a": 2, "z": 1},
            )
            self.assertEqual(list(output.parent.glob(f".{output.name}.*.tmp")), [])

    def test_cli_requires_token_without_allow_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog = Path(temporary) / "catalog.json"
            output = Path(temporary) / "metadata.json"
            catalog.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "repository_url": "https://github.com/Alpha/One",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                with redirect_stderr(StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        main(
                            [
                                "--catalog",
                                str(catalog),
                                "--output",
                                str(output),
                            ]
                        )
            self.assertEqual(raised.exception.code, 2)
            self.assertFalse(output.exists())

    def test_allow_empty_writes_report_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog = Path(temporary) / "catalog.json"
            output = Path(temporary) / "metadata.json"
            catalog.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "repository_url": "https://github.com/Alpha/One",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                with redirect_stdout(StringIO()):
                    self.assertEqual(
                        main(
                            [
                                "--catalog",
                                str(catalog),
                                "--output",
                                str(output),
                                "--allow-empty",
                            ]
                        ),
                        0,
                    )
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["counts"]["requested"], 1)
            self.assertEqual(report["counts"]["fetched"], 0)
            self.assertEqual(report["counts"]["failed"], 1)
            self.assertEqual(report["errors"][0]["type"], "authentication")

    def test_cli_accepts_github_token_and_batch_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog = Path(temporary) / "catalog.json"
            output = Path(temporary) / "metadata.json"
            catalog.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "repository_url": "https://github.com/Alpha/One",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {"GITHUB_TOKEN": "github-secret"},
                clear=True,
            ):
                with mock.patch(
                    "fetch_github_metadata.fetch_repository_metadata",
                    return_value=({}, []),
                ) as fetch:
                    with redirect_stdout(StringIO()):
                        self.assertEqual(
                            main(
                                [
                                    "--catalog",
                                    str(catalog),
                                    "--output",
                                    str(output),
                                    "--batch-size",
                                    "7",
                                ]
                            ),
                            0,
                        )
            fetched_requests, token, batch_size = fetch.call_args.args
            self.assertEqual(
                [request.url for request in fetched_requests],
                ["https://github.com/alpha/one"],
            )
            self.assertEqual(token, "github-secret")
            self.assertEqual(batch_size, 7)


if __name__ == "__main__":
    unittest.main()
