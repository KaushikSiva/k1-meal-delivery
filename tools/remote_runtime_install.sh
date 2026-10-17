#!/usr/bin/env bash
# Authorized single VM only. Start a logged job once; never retry a partial install blindly.
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
mkdir -p "$task_root"
if ! mkdir "$task_root/runtime-install.started" 2>/dev/null; then
  echo "Runtime install already launched; inspect runtime-install.log and .exit."
  exit 0
fi
cat > "$task_root/install-runtime-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/runtime-install.exit"' EXIT
cd "$task_root"
date -u
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libglu1-mesa
mkdir -p downloads
cd downloads
curl -fL --retry 3 -o uv.tar.gz https://github.com/astral-sh/uv/releases/download/0.10.0/uv-x86_64-unknown-linux-gnu.tar.gz
curl -fL --retry 3 -o uv.tar.gz.sha256 https://github.com/astral-sh/uv/releases/download/0.10.0/uv-x86_64-unknown-linux-gnu.tar.gz.sha256
python3 - <<'PY'
import hashlib
from pathlib import Path
expected = Path('uv.tar.gz.sha256').read_text().split()[0]
assert hashlib.sha256(Path('uv.tar.gz').read_bytes()).hexdigest() == expected
print('Official uv archive checksum verified')
PY
tar -xzf uv.tar.gz
cd "$task_root"
downloads/uv-x86_64-unknown-linux-gnu/uv venv --python 3.11.13 --seed .venv
source .venv/bin/activate
export PATH="$task_root/downloads/uv-x86_64-unknown-linux-gnu:$PATH"
export PIP_NO_CACHE_DIR=1
export OMNI_KIT_ACCEPT_EULA=YES
python -m pip install 'isaacsim[all,extscache]==5.1.0' --extra-index-url https://pypi.nvidia.com
# flatdict's legacy setup imports pkg_resources, removed in newer setuptools.
# wheel0.45 also remains compatible with IsaacSim's packaging23 pin.
python -m pip install 'setuptools==80.9.0' 'wheel==0.45.1'
python -m pip install --no-build-isolation flatdict==4.0.1
python -m pip install torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128
git clone --depth 1 --branch v2.3.2 https://github.com/isaac-sim/IsaacLab.git
test "$(git -C IsaacLab rev-parse HEAD)" = 37ddf626871758333d6ed89cf64ad702aef127d0
cd IsaacLab
./isaaclab.sh --install rsl_rl
cd "$task_root"
python -m pip freeze > runtime-packages.txt
python - <<'PY'
import importlib.metadata as md
import json
import platform
from pathlib import Path
import torch
assert torch.cuda.is_available()
x = torch.ones(32, device='cuda')
assert float((x @ x).cpu()) == 32.0
Path('runtime-installed.json').write_text(json.dumps({
    'python': platform.python_version(),
    'isaacsim': md.version('isaacsim'), 'isaaclab': md.version('isaaclab'),
    'torch': torch.__version__, 'cuda': torch.version.cuda,
    'gpu': torch.cuda.get_device_name(),
    'cuda_tensor_test': 'passed',
    'simulator_startup_verified': False,
}, indent=2))
print(Path('runtime-installed.json').read_text())
PY
df -h "$task_root"
date -u
JOB
nohup bash "$task_root/install-runtime-job.sh" > "$task_root/runtime-install.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/runtime-install.pid"
echo "Runtime install launched; PID $(cat "$task_root/runtime-install.pid")."
