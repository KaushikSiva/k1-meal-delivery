#!/usr/bin/env bash
# Prepare only the authorized K1 VM's installed NVIDIA driver holds; no install.
set -euo pipefail
python3 - <<'PY'
import json
from pathlib import Path
import subprocess

root = Path.home() / "workspace/k1-runtime"
root.mkdir(parents=True, exist_ok=True)
holds = set(subprocess.check_output(["apt-mark", "showhold"], text=True).splitlines())
rows = subprocess.check_output(["dpkg-query", "-W", "-f=${binary:Package}\t${db:Status-Abbrev}\t${Version}\n"], text=True)
installed = {p: version for row in rows.splitlines() for p, state, version in [row.split("\t")]
             if len(state) > 1 and state[1] == "i"}
selected = sorted(p for p in holds & installed.keys() if p.startswith("nvidia-")
                  and not any(x in p for x in ("container", "docker", "runtime")))
audit = root / "driver-holds-before.json"
if not audit.exists():
    audit.write_text(json.dumps({"unheld_packages": selected,
                                "installed_nvidia": {p: v for p, v in installed.items() if "nvidia" in p}}, indent=2))
print("Installed driver holds to release:", selected, flush=True)
if selected:
    subprocess.run(["sudo", "apt-mark", "unhold", *selected], check=True)
result = subprocess.run(["sudo", "apt-get", "--simulate", "install", "--no-install-recommends",
                         "nvidia-driver-580-open"], capture_output=True, text=True)
(root / "driver-install-plan.txt").write_text(result.stdout + result.stderr)
print(result.stdout + result.stderr, flush=True)
if result.returncode:
    if selected:
        subprocess.run(["sudo", "apt-mark", "hold", *selected], check=True)
    print("Dry run failed; prior holds restored. No driver installed.")
else:
    print("Dry run succeeded. No driver installed; review plan before applying.")
PY
