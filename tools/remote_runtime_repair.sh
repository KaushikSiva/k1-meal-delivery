#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
if ! mkdir "$task_root/runtime-repair.started" 2>/dev/null; then
  echo "Runtime repair already launched; inspect log and .exit."
  exit 0
fi
cat > "$task_root/repair-runtime-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/runtime-repair.exit"' EXIT
cd "$task_root"
source .venv/bin/activate
export PATH="$task_root/downloads/uv-x86_64-unknown-linux-gnu:$PATH"
python -m pip install 'setuptools==80.9.0' 'wheel==0.45.1'
python -m pip install --no-build-isolation flatdict==4.0.1
uv pip install -e IsaacLab/source/isaaclab
python -m pip freeze > runtime-packages.txt
python - <<'PY'
import json,platform,torch,importlib.metadata as md
from pathlib import Path
assert torch.cuda.is_available()
assert float((torch.ones(32,device='cuda') @ torch.ones(32,device='cuda')).cpu()) == 32
d={'python':platform.python_version(),'isaacsim':md.version('isaacsim'),'isaaclab':md.version('isaaclab'),
   'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(),
   'cuda_tensor_test':'passed','simulator_startup_verified':False}
Path('runtime-installed.json').write_text(json.dumps(d,indent=2));print(json.dumps(d,indent=2))
PY
python -m pip check
JOB
nohup bash "$task_root/repair-runtime-job.sh" > "$task_root/runtime-repair.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/runtime-repair.pid"
echo "Runtime repair launched."
