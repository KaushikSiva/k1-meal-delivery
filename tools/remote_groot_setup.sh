#!/usr/bin/env bash
# Isolated official GR00T prerequisites; no optimizer update or robot actuation.
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
chmod 600 "$task_root/.env.huggingface"
if ! mkdir "$task_root/groot-setup-01.started" 2>/dev/null; then
  echo 'GR00T setup already launched; inspect existing PID/log/exit.'
  exit 0
fi
cat > "$task_root/groot-setup-01-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/groot-setup-01.exit"' EXIT
python3 - <<'PY'
import shutil
from pathlib import Path
free=shutil.disk_usage(Path.home()/'workspace/k1-runtime').free
print('Free disk GiB:',round(free/2**30,2))
assert free>35*2**30,'Insufficient disk headroom for isolated model setup'
PY
export GIT_LFS_SKIP_SMUDGE=1
git clone --filter=blob:none --no-checkout https://github.com/NVIDIA/Isaac-GR00T.git "$task_root/Isaac-GR00T"
cd "$task_root/Isaac-GR00T"
git checkout dac54b313160c201c450f97df0fd74ebd379c892
git submodule update --init --recursive --depth 1
export UV_PROJECT_ENVIRONMENT="$task_root/.venv-groot"
"$task_root/tools/uv-bootstrap/bin/uv" sync --frozen --python 3.12.12
source "$task_root/.venv-groot/bin/activate"
"$task_root/tools/uv-bootstrap/bin/uv" pip check --python "$task_root/.venv-groot/bin/python"
mkdir -p "$task_root/evidence/groot-setup-01"
"$task_root/tools/uv-bootstrap/bin/uv" pip freeze --python "$task_root/.venv-groot/bin/python" > "$task_root/evidence/groot-setup-01/requirements.freeze.txt"
set -a
source "$task_root/.env.huggingface"
set +a
export HF_HUB_DISABLE_TELEMETRY=1
python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import torch,gr00t
from huggingface_hub import snapshot_download
r=Path.home()/'workspace/k1-runtime'
report={'started_at_utc':datetime.now(timezone.utc).isoformat(),'training_performed':False,
        'purpose':'isolated GR00T import and pinned model download, not inference',
        'source_revision':'dac54b313160c201c450f97df0fd74ebd379c892',
        'torch':torch.__version__,'models':{}}
for repo,revision,name in [
 ('nvidia/GR00T-N1.7-3B','2fc962b973bccdd5d8ce4f67cc63b264d6886495','groot_n1_7'),
 ('nvidia/Cosmos-Reason2-2B','9ce19a195e423419c349abfc86fd07178b230561','cosmos_reason2')]:
 target=r/'models'/name
 snapshot_download(repo_id=repo,revision=revision,local_dir=target,
    allow_patterns=['*.json','*.safetensors','*.model','*.txt','*.py','README.md','LICENSE*','*.jinja'])
 artifacts={}
 for p in target.rglob('*'):
  if not p.is_file() or '.cache' in p.parts:continue
  h=hashlib.sha256()
  with p.open('rb') as f:
   while data:=f.read(8*1024*1024):h.update(data)
  artifacts[str(p.relative_to(target))]={'bytes':p.stat().st_size,'sha256':h.hexdigest()}
 report['models'][repo]={'revision':revision,'local_path':str(target),'artifacts':artifacts}
report.update(status='downloaded_import_verified',finished_at_utc=datetime.now(timezone.utc).isoformat())
(r/'evidence/groot-setup-01/manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print('GR00T prerequisites verified; no training or inference performed.')
PY
JOB
nohup bash "$task_root/groot-setup-01-job.sh" > "$task_root/groot-setup-01.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/groot-setup-01.pid"
echo 'Isolated GR00T prerequisite setup launched.'
