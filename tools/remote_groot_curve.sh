#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
if ! mkdir "$task_root/groot-curve-03.started" 2>/dev/null; then
 echo 'GR00T curve already launched; inspect existing evidence.'
 exit 0
fi
cat > "$task_root/groot-curve-03-job.sh" <<'JOB'
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/groot-curve-03.exit"' EXIT
while ! test -f "$task_root/k1-payload-realism-01.exit" || ! test -f "$task_root/groot-data-01.exit"; do sleep 5; done
test "$(cat "$task_root/groot-data-01.exit")" = 0
while ! test -f "$task_root/groot-ffmpeg-01.exit"; do sleep 5; done
test "$(cat "$task_root/groot-ffmpeg-01.exit")" = 0
set -a
source "$task_root/.env.huggingface"
source "$task_root/.env.wandb"
set +a
export PYTHONPATH="$task_root/project:$task_root/Isaac-GR00T"
export WANDB_MODE=online WANDB_PROJECT=k1-meal-delivery-20261017 WANDB_ENTITY=kaushik-siva88
export WANDB_DISABLE_GIT=true WANDB_DISABLE_CODE=true WANDB_CONSOLE=off
export WANDB_NAME=groot-curve-03 WANDB_RUN_ID=groot-curve-03 GROOT_COMMIT_HASH=dac54b313160c201c450f97df0fd74ebd379c892
export HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false
cd "$task_root/Isaac-GR00T"
"$task_root/.venv-groot/bin/python" "$task_root/project/training/finetune_groot_curve.py" --runtime "$task_root" --output "$task_root/evidence/groot-curve-03" --steps 500
JOB
nohup bash "$task_root/groot-curve-03-job.sh" > "$task_root/groot-curve-03.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/groot-curve-03.pid"
echo 'GR00T 500-update run with fixed validation every25steps queued with real data and live W&B logging.'
