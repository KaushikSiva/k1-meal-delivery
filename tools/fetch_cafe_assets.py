#!/usr/bin/env python3
"""Fetch the exact CC0 Poly Haven files in sim/cafe_assets.json; verify SHA-256."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def fetch_assets(lock: Path, destination: Path):
    entries = json.loads(lock.read_text())["files"]
    root = destination.resolve()

    def fetch(entry):
        target = (root / entry["path"]).resolve()
        if not target.is_relative_to(root):
            raise ValueError("Asset path escapes destination")
        if target.exists():
            data = target.read_bytes()
        else:
            request = urllib.request.Request(entry["url"], headers={"User-Agent": "K1-Meal-Delivery-Research/0.1"})
            with urllib.request.urlopen(request, timeout=120) as response:
                data = response.read()
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"Asset integrity mismatch: {entry['path']}")
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".partial")
            temporary.write_bytes(data)
            temporary.replace(target)
        return entry["path"]

    with ThreadPoolExecutor(max_workers=3) as pool:
        for path in pool.map(fetch, entries):
            print("Verified", path, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("sim/cafe_assets.json"))
    parser.add_argument("--destination", type=Path, default=Path("sim/vendor/cafe-assets"))
    args = parser.parse_args()
    fetch_assets(args.lock, args.destination)
