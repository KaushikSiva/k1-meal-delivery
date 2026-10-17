#!/usr/bin/env python3
"""Small You.com search client. Credentials stay in environment or ignored .env.

Usage: python3 tools/you_search.py 'query' --domain docs.booster.tech --output path.json
Search results are source leads, never measured robot properties.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://ydc-index.io/v1/search"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_key():
    value = os.environ.get("YDC_API_KEY", "").strip()
    if value:
        return value
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "YDC_API_KEY":
                value = value.strip().strip("\"'")
                if value:
                    return value
    raise ValueError("YDC_API_KEY is missing; configure it locally without committing it.")


def search(query, count=5, domains=None):
    key = read_key()
    body = {"query": query, "count": count}
    if domains:
        body["include_domains"] = domains
    request = Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={"X-API-Key": key, "Content-Type": "application/json"},
        method="POST",
    )
    with build_opener(NoRedirect).open(request, timeout=45) as response:
        payload = json.load(response)
    results = payload.get("results", {}).get("web", [])
    if not isinstance(results, list):
        raise ValueError("Unexpected You.com response shape.")
    record = {
        "provider": "You.com",
        "endpoint": ENDPOINT,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "query": query,
        "include_domains": domains or [],
        "evidence_kind": "web_search_leads_not_physical_measurements",
        "results": [
            {field: item.get(field) for field in ("title", "url", "description", "snippets")}
            for item in results if isinstance(item, dict)
        ],
    }
    # Even an unexpected upstream echo must never expose the credential.
    return json.loads(json.dumps(record).replace(key, "[REDACTED]"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--domain", action="append", default=[])
    parser.add_argument("--count", type=int, default=5, choices=range(1, 11), metavar="1..10")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Output already exists; preserve research provenance with a new path.")
    try:
        record = search(args.query, args.count, args.domain)
        text = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x") as handle:
                handle.write(text)
            print(f"Saved {len(record['results'])} source leads to {args.output}")
        else:
            print(text, end="")
    except HTTPError as error:
        print(f"You.com HTTP {error.code}; response body omitted to protect credentials.", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, OSError):
        print("You.com request or output failed; check network/access/path. Secrets omitted.", file=sys.stderr)
        return 1
    except (ValueError, TypeError, AttributeError):
        print("Missing credential or invalid response; no credential/body printed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
