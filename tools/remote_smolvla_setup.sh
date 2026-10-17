#!/usr/bin/env bash
# Isolated public-model prerequisite installation; no training or robot actuation.
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
if ! mkdir "$task_root/smolvla-setup-03.started" 2>/dev/null; then
  echo 'Setup already launched; inspect the existing PID/log/exit.'
  exit 0
fi
cat > "$task_root/smolvla-setup-03-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/smolvla-setup-03.exit"' EXIT
# Use the existing pip executable only as an installer into a separate target;
# this does not install or replace packages in the Isaac environment.
"$task_root/.venv/bin/python" -m pip install --disable-pip-version-check --target "$task_root/tools/uv-bootstrap" 'uv==0.9.5'
"$task_root/tools/uv-bootstrap/bin/uv" python install 3.12.12
"$task_root/tools/uv-bootstrap/bin/uv" venv --seed --python 3.12.12 "$task_root/.venv-smolvla"
source "$task_root/.venv-smolvla/bin/activate"
python -m pip install --disable-pip-version-check 'pip==25.3'
python -m pip install --disable-pip-version-check 'torch==2.9.0' 'torchvision==0.24.0' --index-url https://download.pytorch.org/whl/cu128
python -m pip install --disable-pip-version-check 'lerobot[smolvla,training]==0.6.1' 'torch==2.9.0' 'torchvision==0.24.0' 'torchcodec==0.8.0'
python -m pip check
mkdir -p "$task_root/evidence/smolvla-setup-03"
python -m pip freeze > "$task_root/evidence/smolvla-setup-03/requirements.freeze.txt"
export HF_HUB_DISABLE_TELEMETRY=1
python - <<'PY'
from pathlib import Path
import hashlib,json,time
from datetime import datetime,timezone
import torch
from huggingface_hub import snapshot_download
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
r=Path.home()/'workspace/k1-runtime'
report={'started_at_utc':datetime.now(timezone.utc).isoformat(),'training_performed':False,
        'purpose':'isolated dependency import and public pretrained snapshot download',
        'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'models':{}}
for repo,revision,name in [
 ('lerobot/smolvla_base','5e8d12a6e2975b0e5e5fce7c8caf47c371d257b6','smolvla_base'),
 ('HuggingFaceTB/SmolVLM2-500M-Video-Instruct','7b375e1b73b11138ff12fe22c8f2822d8fe03467','smolvlm2')]:
 target=r/'models'/name
 snapshot_download(repo_id=repo,revision=revision,local_dir=target,
                   allow_patterns=['*.json','*.safetensors','*.model','*.txt','*.py','README.md','LICENSE*'])
 artifacts={}
 for p in target.rglob('*'):
  if not p.is_file() or '.cache' in p.parts:continue
  h=hashlib.sha256()
  with p.open('rb') as f:
   while b:=f.read(8*1024*1024):h.update(b)
  artifacts[str(p.relative_to(target))]={'bytes':p.stat().st_size,'sha256':h.hexdigest()}
 report['models'][repo]={'revision':revision,'local_path':str(target),'artifacts':artifacts}
report.update(status='downloaded_import_verified',finished_at_utc=datetime.now(timezone.utc).isoformat())
(r/'evidence/smolvla-setup-03/manifest.json').write_text(json.dumps(report,indent=2))
print('Public snapshots downloaded, policy import verified; no fine-tuning performed.')
PY
JOB
nohup bash "$task_root/smolvla-setup-03-job.sh" > "$task_root/smolvla-setup-03.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/smolvla-setup-03.pid"
echo 'Isolated SmolVLA setup launched.'
