#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
test "$(cat "$task_root/k1-loaded-01.exit")" = 0
if ! mkdir "$task_root/k1-ppo-02.started" 2>/dev/null; then
  echo "PPO pilot already launched; inspect its manifest and log."
  exit 0
fi
cat > "$task_root/k1-ppo-02-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/k1-ppo-02.exit"' EXIT
tar -xzf "$task_root/k1-ppo-02-source.tar.gz" -C "$task_root/project"
cd "$task_root/project"
source "$task_root/.venv/bin/activate"
export OMNI_KIT_ACCEPT_EULA=YES
python training/train_carrying.py --output "$task_root/evidence/k1-ppo-02" --num-envs 32 --iterations 100 --horizon 64 --seed 7102
python -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"]=="trained"' "$task_root/evidence/k1-ppo-02/manifest.json"
tar -czf "$task_root/k1-ppo-02-evidence.tar.gz" --exclude=converted --exclude='*.pt' -C "$task_root/evidence/k1-ppo-02" .
JOB
nohup bash "$task_root/k1-ppo-02-job.sh" > "$task_root/k1-ppo-02.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/k1-ppo-02.pid"
echo "Real-physics PPO pilot launched."
