#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
# Training must finish before the separate rendered evaluation starts.
test "$(cat "$task_root/k1-ppo-02.exit")" = 0
if ! mkdir "$task_root/k1-loaded-ppo02-eval01.started" 2>/dev/null; then
  echo "Walk already launched; inspect k1-loaded-ppo02-eval01.log and .exit."
  exit 0
fi
cat > "$task_root/k1-loaded-ppo02-eval01-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/k1-loaded-ppo02-eval01.exit"' EXIT
tar -xzf "$task_root/k1-loaded-ppo02-eval01-source.tar.gz" -C "$task_root/project"
cd "$task_root/project"
source "$task_root/.venv/bin/activate"
export OMNI_KIT_ACCEPT_EULA=YES
python deployment/export_residual.py "$task_root/evidence/k1-ppo-02/final.pt" "$task_root/evidence/k1-ppo-02-export/residual.pt"
python sim/run_k1_isaac.py --output "$task_root/evidence/k1-loaded-ppo02-eval01" --duration 15 --speed 0.35 --loaded --residual-checkpoint "$task_root/evidence/k1-ppo-02/final.pt"
python -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"]=="tested"' "$task_root/evidence/k1-loaded-ppo02-eval01/manifest.json"
tar -czf "$task_root/k1-loaded-ppo02-eval01-evidence.tar.gz" --exclude=converted -C "$task_root/evidence/k1-loaded-ppo02-eval01" .
JOB
nohup bash "$task_root/k1-loaded-ppo02-eval01-job.sh" > "$task_root/k1-loaded-ppo02-eval01.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/k1-loaded-ppo02-eval01.pid"
echo "Supported payload diagnostic launched."
