#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
run_name=hand-isaac-04
if ! mkdir "$task_root/$run_name.started" 2>/dev/null; then exit 0; fi
cat > "$task_root/$run_name-job.sh" <<'JOB'
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/hand-isaac-04.exit"' EXIT
"$task_root/.venv/bin/python" -m pip install 'mujoco==3.16.0'
export ACCEPT_EULA=Y OMNI_KIT_ACCEPT_EULA=YES
cd "$task_root/project"
"$task_root/.venv/bin/python" sim/run_k1_hand_carry_isaac.py --output "$task_root/evidence/hand-isaac-04" --duration 15 --speed .4 --tracking-evaluator
JOB
nohup bash "$task_root/$run_name-job.sh" > "$task_root/$run_name.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/$run_name.pid"
echo 'Free hand-contact Isaac trial launched.'
