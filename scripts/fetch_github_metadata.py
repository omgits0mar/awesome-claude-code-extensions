#!/usr/bin/env python3
"""Fetch GitHub repository metadata used by the catalog website.

Repository URLs come from the canonical catalog. The output remains useful when
individual GraphQL batches or repositories fail: successful records are kept and
errors are reported alongside explicit counts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
DEFAULT_BATCH_SIZE = 50
OWNER_PATTERN = re.compile(
    r"(?=.{1,39}\Z)[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
)
REPOSITORY_PATTERN = re.compile(r"(?=.{1,100}\Z)[A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class RepositoryRequest:
    """A normalized repository URL and its GraphQL coordinates."""

    url: str
    owner: str
    name: str


GraphQLRequest = Callable[
    [str, Mapping[str, str], str],
    Mapping[str, Any],
]


def utc_timestamp() -> str:
    """Return a compact, timezone-explicit timestamp."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def normalize_github_repository_url(value: object) -> RepositoryRequest:
    """Validate and normalize a public github.com repository URL.

    GitHub owner and repository names are case-insensitive, so lower-casing the
    normalized URL also makes de-duplication stable. A trailing slash, query,
    fragment, and conventional ``.git`` suffix do not change repository identity.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("repository_url must be a non-empty string")

    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("repository_url must use HTTP or HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("repository_url must not contain credentials")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("repository_url contains an invalid port") from exc
    if port is not None:
        raise ValueError("repository_url must not contain a port")
    if (parsed.hostname or "").lower() not in {"github.com", "www.github.com"}:
        raise ValueError("repository_url must use the github.com host")
    if "%" in parsed.path:
        raise ValueError("repository_url must not contain escaped path characters")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise ValueError("repository_url must point to a repository root")
    owner, name = parts
    if name.lower().endswith(".git"):
        name = name[:-4]
    if not OWNER_PATTERN.fullmatch(owner):
        raise ValueError("repository_url contains an invalid owner name")
    if not REPOSITORY_PATTERN.fullmatch(name) or name in {".", ".."}:
        raise ValueError("repository_url contains an invalid repository name")

    owner = owner.lower()
    name = name.lower()
    return RepositoryRequest(
        url=f"https://github.com/{owner}/{name}",
        owner=owner,
        name=name,
    )


def load_catalog(path: Path) -> dict[str, Any]:
    """Load a catalog and validate the small portion this script consumes."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read catalog {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise ValueError(f"catalog {path} must contain an entries array")
    return payload


def collect_repository_requests(
    catalog: Mapping[str, Any],
) -> tuple[list[RepositoryRequest], list[dict[str, Any]]]:
    """Collect, validate, de-duplicate, and sort catalog repository URLs."""
    requests: dict[str, RepositoryRequest] = {}
    errors: list[dict[str, Any]] = []
    entries = catalog.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("catalog must contain an entries array")

    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            errors.append(
                {
                    "type": "invalid_catalog_entry",
                    "entry_index": index,
                    "message": "catalog entry must be an object",
                }
            )
            continue
        raw_url = entry.get("repository_url")
        try:
            request = normalize_github_repository_url(raw_url)
        except ValueError as exc:
            error: dict[str, Any] = {
                "type": "invalid_repository_url",
                "entry_index": index,
                "repository_url": raw_url,
                "message": str(exc),
            }
            if isinstance(entry.get("id"), str):
                error["entry_id"] = entry["id"]
            errors.append(error)
            continue
        requests.setdefault(request.url, request)

    return [requests[url] for url in sorted(requests)], errors


def build_graphql_batch(
    repositories: Sequence[RepositoryRequest],
) -> tuple[str, dict[str, str], dict[str, RepositoryRequest]]:
    """Build one aliased GraphQL query and its variables."""
    if not repositories:
        raise ValueError("cannot build an empty GraphQL batch")

    definitions: list[str] = []
    selections: list[str] = []
    variables: dict[str, str] = {}
    aliases: dict[str, RepositoryRequest] = {}
    fields = """\
      nameWithOwner
      url
      stargazerCount
      forkCount
      isArchived
      isDisabled
      isFork
      pushedAt
      updatedAt
      primaryLanguage {
        name
        color
      }
      licenseInfo {
        key
        name
        nickname
        spdxId
        url
      }
      owner {
        avatarUrl
      }
      openGraphImageUrl"""

    for index, repository in enumerate(repositories):
        alias = f"repo{index}"
        owner_variable = f"owner{index}"
        name_variable = f"name{index}"
        definitions.extend(
            [
                f"${owner_variable}: String!",
                f"${name_variable}: String!",
            ]
        )
        variables[owner_variable] = repository.owner
        variables[name_variable] = repository.name
        aliases[alias] = repository
        selections.append(
            f"""\
  {alias}: repository(
    owner: ${owner_variable}
    name: ${name_variable}
  ) {{
{fields}
  }}"""
        )

    query = (
        "query RepositoryMetadata("
        + ", ".join(definitions)
        + ") {\n"
        + "\n".join(selections)
        + "\n}\n"
    )
    return query, variables, aliases


def graphql_request(
    query: str,
    variables: Mapping[str, str],
    token: str,
) -> Mapping[str, Any]:
    """Send one request to GitHub's GraphQL API."""
    body = json.dumps(
        {"query": query, "variables": dict(variables)},
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "awesome-claude-code-catalog-metadata/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            response_body = response.read()
    except urllib.error.HTTPError as exc:
        # GitHub can return useful GraphQL errors with a non-2xx response.
        response_body = exc.read()
        try:
            payload = json.loads(response_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as parse_exc:
            raise RuntimeError(f"GitHub API returned HTTP {exc.code}") from parse_exc
        if isinstance(payload, Mapping) and payload.get("errors"):
            return payload
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}") from exc
    except (OSError, TimeoutError) as exc:
        raise RuntimeError(f"GitHub API request failed: {exc}") from exc

    try:
        payload = json.loads(response_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("GitHub API returned invalid JSON") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError("GitHub API returned a non-object response")
    return payload


def normalized_metadata(node: Mapping[str, Any]) -> dict[str, Any]:
    """Retain the documented output fields in a stable order."""
    return {
        "nameWithOwner": node.get("nameWithOwner"),
        "url": node.get("url"),
        "stargazerCount": node.get("stargazerCount"),
        "forkCount": node.get("forkCount"),
        "isArchived": node.get("isArchived"),
        "isDisabled": node.get("isDisabled"),
        "isFork": node.get("isFork"),
        "pushedAt": node.get("pushedAt"),
        "updatedAt": node.get("updatedAt"),
        "primaryLanguage": node.get("primaryLanguage"),
        "licenseInfo": node.get("licenseInfo"),
        "owner": node.get("owner"),
        "openGraphImageUrl": node.get("openGraphImageUrl"),
    }


def parse_graphql_payload(
    payload: Mapping[str, Any],
    aliases: Mapping[str, RepositoryRequest],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Extract successful aliases while preserving GitHub GraphQL errors."""
    repositories: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    data = payload.get("data")
    data_object = data if isinstance(data, Mapping) else {}

    raw_errors = payload.get("errors", [])
    if not isinstance(raw_errors, list):
        raw_errors = [
            {"message": "GitHub GraphQL response contained a malformed errors field"}
        ]
    errored_urls: set[str] = set()
    for raw_error in raw_errors:
        if not isinstance(raw_error, Mapping):
            raw_error = {"message": str(raw_error)}
        path = raw_error.get("path")
        repository_url = None
        if isinstance(path, list) and path:
            request = aliases.get(str(path[0]))
            if request:
                repository_url = request.url
                errored_urls.add(repository_url)
        error: dict[str, Any] = {
            "type": "graphql",
            "message": str(raw_error.get("message", "Unknown GraphQL error")),
        }
        if isinstance(path, list):
            error["path"] = path
        if repository_url:
            error["repository_url"] = repository_url
        errors.append(error)

    for alias, request in aliases.items():
        node = data_object.get(alias)
        if isinstance(node, Mapping):
            repositories[request.url] = normalized_metadata(node)
        elif request.url not in errored_urls:
            errors.append(
                {
                    "type": "repository_unavailable",
                    "repository_url": request.url,
                    "message": "GitHub returned no repository metadata",
                }
            )

    return repositories, errors


def fetch_repository_metadata(
    repositories: Sequence[RepositoryRequest],
    token: str,
    batch_size: int,
    request_fn: GraphQLRequest = graphql_request,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Fetch every batch, continuing after request-level failures."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    metadata: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    for offset in range(0, len(repositories), batch_size):
        batch = repositories[offset : offset + batch_size]
        query, variables, aliases = build_graphql_batch(batch)
        try:
            payload = request_fn(query, variables, token)
            batch_metadata, batch_errors = parse_graphql_payload(payload, aliases)
        except Exception as exc:  # Keep later batches and prior successful results.
            errors.append(
                {
                    "type": "request",
                    "repository_urls": [repository.url for repository in batch],
                    "message": str(exc),
                }
            )
            continue
        metadata.update(batch_metadata)
        errors.extend(batch_errors)

    return metadata, errors


def sort_errors(errors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Make output stable even if an API changes error ordering."""
    copied = [dict(error) for error in errors]
    return sorted(
        copied,
        key=lambda error: (
            str(error.get("type", "")),
            str(error.get("repository_url", "")),
            json.dumps(error.get("repository_urls", []), sort_keys=True),
            str(error.get("entry_id", "")),
            int(error.get("entry_index", -1)),
            str(error.get("message", "")),
            json.dumps(error.get("path", []), sort_keys=True),
        ),
    )


def build_report(
    *,
    catalog_entry_count: int,
    requests: Sequence[RepositoryRequest],
    repositories: Mapping[str, Mapping[str, Any]],
    errors: Sequence[Mapping[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the deterministic on-disk report structure."""
    ordered_repositories = {
        url: dict(repositories[url]) for url in sorted(repositories)
    }
    ordered_errors = sort_errors(errors)
    invalid_count = sum(
        error.get("type") in {"invalid_catalog_entry", "invalid_repository_url"}
        for error in ordered_errors
    )
    return {
        "generated_at": generated_at or utc_timestamp(),
        "counts": {
            "catalog_entries": catalog_entry_count,
            "requested": len(requests),
            "fetched": len(ordered_repositories),
            "failed": len(requests) - len(ordered_repositories),
            "invalid": invalid_count,
            "errors": len(ordered_errors),
        },
        "repositories": ordered_repositories,
        "errors": ordered_errors,
    }


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write formatted JSON without exposing a partially-written destination."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(
                payload,
                temporary,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def positive_integer(value: str) -> int:
    """Argparse type for positive integer options."""
    try:
        integer = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if integer < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return integer


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=ROOT / "catalog" / "catalog.json",
        help="Canonical catalog JSON input.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "catalog" / "github-metadata.json",
        help="Metadata report output.",
    )
    parser.add_argument(
        "--batch-size",
        type=positive_integer,
        default=DEFAULT_BATCH_SIZE,
        help=f"Repositories per GraphQL request (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Write an empty metadata report when no GitHub token is available.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = argument_parser()
    args = parser.parse_args(argv)
    try:
        catalog = load_catalog(args.catalog)
        requests, validation_errors = collect_repository_requests(catalog)
    except ValueError as exc:
        parser.error(str(exc))

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    errors = list(validation_errors)
    if not token:
        if not args.allow_empty:
            parser.error(
                "GH_TOKEN or GITHUB_TOKEN is required; "
                "pass --allow-empty to write a report without metadata"
            )
        errors.append(
            {
                "type": "authentication",
                "message": (
                    "No GH_TOKEN or GITHUB_TOKEN was available; "
                    "metadata fetching was skipped"
                ),
            }
        )
        repositories: dict[str, dict[str, Any]] = {}
    else:
        repositories, fetch_errors = fetch_repository_metadata(
            requests,
            token,
            args.batch_size,
        )
        errors.extend(fetch_errors)

    report = build_report(
        catalog_entry_count=len(catalog["entries"]),
        requests=requests,
        repositories=repositories,
        errors=errors,
    )
    atomic_write_json(args.output, report)
    print(
        f"Wrote {report['counts']['fetched']:,} of "
        f"{report['counts']['requested']:,} repositories to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
