#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
test "$(cat "$task_root/smolvla-setup-03.exit")" = 0
if ! mkdir "$task_root/smolvla-probe-01.started" 2>/dev/null; then
  echo 'Probe already launched; inspect existing PID/log/exit.'
  exit 0
fi
cat > "$task_root/smolvla-probe-01-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/smolvla-probe-01.exit"' EXIT
# Serialize GPU work with the already running rendered simulation.
while [ ! -f "$task_root/k1-appearance-02.exit" ]; do
  kill -0 "$(cat "$task_root/k1-appearance-02.pid")"
  sleep 2
done
test "$(cat "$task_root/k1-appearance-02.exit")" = 0
tar -xzf "$task_root/smolvla-probe-01-source.tar.gz" -C "$task_root/project"
source "$task_root/.venv-smolvla/bin/activate"
export HF_HUB_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export WANDB_MODE=disabled
python "$task_root/project/training/probe_smolvla.py" --runtime "$task_root" --output "$task_root/evidence/smolvla-probe-01"
JOB
nohup bash "$task_root/smolvla-probe-01-job.sh" > "$task_root/smolvla-probe-01.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/smolvla-probe-01.pid"
echo 'SmolVLA plumbing probe queued after the active simulation.'
