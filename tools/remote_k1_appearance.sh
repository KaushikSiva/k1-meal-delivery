#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
test "$(cat "$task_root/k1-cupholder-ppo02-01.exit")" = 0
if ! mkdir "$task_root/k1-appearance-03.started" 2>/dev/null; then
  echo 'Appearance repeat already launched; inspect existing PID/log/exit.'
  exit 0
fi
cat > "$task_root/k1-appearance-03-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/k1-appearance-03.exit"' EXIT
tar -xzf "$task_root/k1-appearance-03-source.tar.gz" -C "$task_root/project"
cd "$task_root/project"
source "$task_root/.venv/bin/activate"
export OMNI_KIT_ACCEPT_EULA=YES
python sim/run_k1_isaac.py --output "$task_root/evidence/k1-appearance-03" --duration 15 --speed .35 --loaded --wide-evaluator --payload-config sim/k1_payload_cupholder.json --reference-colors --residual-checkpoint "$task_root/evidence/k1-ppo-02/final.pt"
python -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"]=="tested"' "$task_root/evidence/k1-appearance-03/manifest.json"
tar -czf "$task_root/k1-appearance-03-evidence.tar.gz" --exclude=converted -C "$task_root/evidence/k1-appearance-03" .
JOB
nohup bash "$task_root/k1-appearance-03-job.sh" > "$task_root/k1-appearance-03.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/k1-appearance-03.pid"
echo 'Reference-color carrying repeat launched.'
