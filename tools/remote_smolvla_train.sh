#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
test "$(cat "$task_root/smolvla-probe-01.exit")" = 0
test -f "$task_root/smolvla-train-02-source-data.tar.gz"
if ! mkdir "$task_root/smolvla-train-02.started" 2>/dev/null; then
  echo 'SmolVLA training already launched; inspect existing PID/log/exit.'
  exit 0
fi
cat > "$task_root/smolvla-train-02-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/smolvla-train-02.exit"' EXIT
mkdir -p "$task_root/smolvla-train-02-input"
tar -xzf "$task_root/smolvla-train-02-source-data.tar.gz" -C "$task_root/smolvla-train-02-input"
source "$task_root/.venv-smolvla/bin/activate"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 WANDB_MODE=disabled
python "$task_root/smolvla-train-02-input/training/finetune_smolvla.py" \
  --runtime "$task_root" --dataset "$task_root/smolvla-train-01-input/sensor-dataset-01" \
  --output "$task_root/evidence/smolvla-train-02"
python -c 'import json,sys; m=json.load(open(sys.argv[1])); assert m["status"]=="trained" and m["optimizer_updates"]==200' "$task_root/evidence/smolvla-train-02/manifest.json"
tar -czf "$task_root/smolvla-train-02-report.tar.gz" -C "$task_root/evidence/smolvla-train-02" manifest.json metrics.json normalization.json policy/config.json
JOB
nohup bash "$task_root/smolvla-train-02-job.sh" > "$task_root/smolvla-train-02.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/smolvla-train-02.pid"
echo 'SmolVLA 200-update pilot launched.'
