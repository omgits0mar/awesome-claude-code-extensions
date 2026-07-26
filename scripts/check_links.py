#!/usr/bin/env python3
"""Check catalog links concurrently and emit a machine-readable report."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never forward a GitHub token to a different redirect host."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and (
            urllib.parse.urlsplit(req.full_url).netloc.lower()
            != urllib.parse.urlsplit(newurl).netloc.lower()
        ):
            redirected.remove_header("Authorization")
        return redirected


OPENER = urllib.request.build_opener(SafeRedirectHandler())


def comparable_url(url: str) -> str:
    """Normalize redirect targets for canonical-URL comparisons."""
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", "")
    )


def response_result(
    original_url: str, response: Any, started: float, method: str | None = None
) -> dict[str, Any]:
    final_url = response.geturl()
    moved = comparable_url(final_url) != comparable_url(original_url)
    result = {
        "url": original_url,
        "status": response.status,
        "result": "redirect" if moved else (
            "ok" if response.status < 400 else "error"
        ),
        "elapsed_ms": round((time.monotonic() - started) * 1000),
    }
    if moved:
        result["final_url"] = final_url
    if method:
        result["method"] = method
    return result


def check(url: str, timeout: float) -> dict[str, Any]:
    headers = {
        "Accept": "text/html",
        "User-Agent": "awesome-claude-code-catalog-link-checker/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, method="HEAD", headers=headers)
    started = time.monotonic()
    try:
        with OPENER.open(request, timeout=timeout) as response:
            return response_result(url, response, started)
    except urllib.error.HTTPError as exc:
        if exc.code in {404, 405}:
            # A few GitHub routes reject or mis-handle HEAD while GET succeeds.
            # Confirm with a tiny ranged GET before declaring the link dead.
            get_headers = dict(headers)
            get_headers["Range"] = "bytes=0-0"
            get_request = urllib.request.Request(url, method="GET", headers=get_headers)
            try:
                with OPENER.open(get_request, timeout=timeout) as response:
                    return response_result(
                        url, response, started, method="GET-fallback"
                    )
            except urllib.error.HTTPError as get_exc:
                exc = get_exc
            except (OSError, TimeoutError) as get_exc:
                return {
                    "url": url,
                    "status": None,
                    "result": "unknown",
                    "error": str(get_exc),
                    "method": "GET-fallback",
                    "elapsed_ms": round((time.monotonic() - started) * 1000),
                }
        # 403 and 429 are indeterminate rate limiting, not proof of a dead project.
        result = "unknown" if exc.code in {403, 429} else "error"
        return {
            "url": url,
            "status": exc.code,
            "result": result,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        }
    except (OSError, TimeoutError) as exc:
        return {
            "url": url,
            "status": None,
            "result": "unknown",
            "error": str(exc),
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100, help="0 checks all links.")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=12)
    parser.add_argument(
        "--max-unknown-rate",
        type=float,
        default=0.10,
        help="Fail when the indeterminate result fraction exceeds this value.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "catalog" / "link-report.json",
    )
    args = parser.parse_args()
    payload = json.loads((ROOT / "catalog" / "catalog.json").read_text(encoding="utf-8"))
    urls = [entry["url"] for entry in payload["entries"]]
    if args.limit:
        # Deterministic spread across the sorted catalog instead of checking only one tier.
        if args.limit < len(urls):
            step = len(urls) / args.limit
            urls = [urls[int(index * step)] for index in range(args.limit)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda url: check(url, args.timeout), urls))
    summary = {
        result: sum(item["result"] == result for item in results)
        for result in ("ok", "error", "redirect", "unknown")
    }
    unknown_rate = summary["unknown"] / len(results) if results else 0.0
    report = {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": summary,
        "unknown_rate": round(unknown_rate, 4),
        "max_unknown_rate": args.max_unknown_rate,
        "results": results,
    }
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {**summary, "unknown_rate": round(unknown_rate, 4)},
            sort_keys=True,
        )
    )
    return 1 if (
        summary["error"]
        or summary["redirect"]
        or unknown_rate > args.max_unknown_rate
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
