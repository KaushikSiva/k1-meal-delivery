#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
test "$(cat "$task_root/mujoco-vla-setup-01.exit")" = 0
if ! mkdir "$task_root/vla-comparison-02.started" 2>/dev/null; then
  echo 'Comparison already launched; inspect existing PID/log/exit.'
  exit 0
fi
cat > "$task_root/vla-comparison-02-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/vla-comparison-02.exit"' EXIT
tar -xzf "$task_root/vla-comparison-02-source.tar.gz" -C "$task_root/project"
source "$task_root/.venv-smolvla/bin/activate"
export PYTHONPATH="$task_root/project/sim/vendor/booster_assets/src:$task_root/project"
export MUJOCO_GL=egl HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 WANDB_MODE=disabled
cd "$task_root/project"
python -c 'from sim.run_k1_sensor_navigation import SensorController; print("Controller imports verified")'
python evaluation/run_vla_comparison.py --output "$task_root/evidence/vla-comparison-02" \
  --checkpoint "$task_root/evidence/smolvla-train-02"
tar -czf "$task_root/vla-comparison-02-evidence.tar.gz" -C "$task_root/evidence/vla-comparison-02" .
JOB
nohup bash "$task_root/vla-comparison-02-job.sh" > "$task_root/vla-comparison-02.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/vla-comparison-02.pid"
echo 'Matched executive/SmolVLA comparison launched.'
