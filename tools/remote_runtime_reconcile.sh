#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
if ! mkdir "$task_root/runtime-reconcile-02.started" 2>/dev/null; then
  echo "Runtime reconciliation already launched; inspect log and .exit."
  exit 0
fi
cat > "$task_root/reconcile-runtime-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/runtime-reconcile-02.exit"' EXIT
cd "$task_root"
source .venv/bin/activate
python -m pip install ipython==8.37.0
python -m pip install 'torchaudio==2.7.0+cu128' --index-url https://download.pytorch.org/whl/cu128
python -m pip install numpy==1.26.0 psutil==5.9.8 typing_extensions==4.12.2 filelock==3.13.1 fsspec==2024.6.1 markupsafe==2.1.3 networkx==3.3 sympy==1.13.3
python - <<'PY'
import json, subprocess,sys
from pathlib import Path
result = subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True)
Path('pip-check.txt').write_text(result.stdout+result.stderr)
lines = [s for s in result.stdout.splitlines() if s]
expected = 'fastapi 0.115.7 has requirement starlette<0.46.0,>=0.40.0, but you have starlette 0.49.1.'
assert result.returncode == 0 or lines == [expected], result.stdout+result.stderr
report = {'pip_check_exit':result.returncode,'known_upstream_conflicts':lines,
          'reason':'IsaacLab2.3.2 pins starlette0.49.1 while IsaacSim5.1 pins fastapi0.115.7. Preserve the explicit Lab pin; no web API service used. Simulator/physics/RGB must be separately tested.',
          'other_dependency_conflicts':[]}
Path('runtime-dependency-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
PY
python -m pip freeze > runtime-packages.txt
JOB
nohup bash "$task_root/reconcile-runtime-job.sh" > "$task_root/runtime-reconcile-02.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/runtime-reconcile-02.pid"
echo "Runtime reconciliation launched."
