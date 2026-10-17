#!/usr/bin/env bash
# Read-only inventory for the specifically authorized K1 GPU instance.
set -euo pipefail
date -u '+%Y-%m-%dT%H:%M:%SZ'
uname -sm
cat /etc/os-release
getconf GNU_LIBC_VERSION
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
free -h
df -h / /tmp
python3 --version
for tool in uv docker git vulkaninfo; do
    command -v "$tool" || true
done
python3 - <<'PY'
import importlib.util
import json
import platform
print(json.dumps({"python": platform.python_version(), "installed_modules": {
    name: importlib.util.find_spec(name) is not None
    for name in ("torch", "isaacsim", "isaaclab", "mujoco")}}, indent=2))
PY
