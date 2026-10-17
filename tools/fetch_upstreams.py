#!/usr/bin/env python3
"""Fetch pinned official sources into ignored sim/vendor, without modifying them."""

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    subprocess.run(args, check=True)


def main():
    lock = json.loads((ROOT / "sim/upstream-lock.json").read_text())
    base = ROOT / "sim/vendor"
    base.mkdir(parents=True, exist_ok=True)
    for item in lock["repositories"]:
        url, revision = item["repository"], item["commit"]
        if not url.startswith("https://github.com/BoosterRobotics/"):
            raise ValueError("Unexpected upstream owner")
        if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
            raise ValueError("Expected an exact Git commit")
        name = url.rsplit("/", 1)[-1]
        target = base / name
        if target.exists():
            head = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
            if head != revision:
                raise RuntimeError(f"Existing {name} has a different revision; preserved unchanged")
            dirty = subprocess.check_output(
                ["git", "-C", str(target), "status", "--porcelain"], text=True
            ).strip()
            if dirty:
                raise RuntimeError(f"Existing {name} has local changes; preserved unchanged")
            print(f"Already pinned: {name} {revision}", flush=True)
            continue
        run(["git", "clone", "--filter=blob:none", "--no-checkout", url, str(target)])
        if name == "booster_assets":
            run(["git", "-C", str(target), "sparse-checkout", "init", "--cone"])
            run(["git", "-C", str(target), "sparse-checkout", "set", "robots/K1", "src"])
        run(["git", "-C", str(target), "checkout", "--detach", revision])
        print(f"Pinned: {name} {revision}", flush=True)


if __name__ == "__main__":
    main()
