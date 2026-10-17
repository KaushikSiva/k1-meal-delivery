#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
# Import must finish, even if nominal PD falls; inspect its manifest first.
test -f "$task_root/k1-import-03.exit"
if ! mkdir "$task_root/k1-walk-04.started" 2>/dev/null; then
  echo "Walk already launched; inspect k1-walk-04.log and .exit."
  exit 0
fi
cat > "$task_root/k1-walk-04-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/k1-walk-04.exit"' EXIT
tar -xzf "$task_root/k1-walk-04-source.tar.gz" -C "$task_root/project"
cd "$task_root/project"
source "$task_root/.venv/bin/activate"
export OMNI_KIT_ACCEPT_EULA=YES
python sim/run_k1_isaac.py --output "$task_root/evidence/k1-walk-04" --duration 15 --speed 0.35
python -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"]=="tested"' "$task_root/evidence/k1-walk-04/manifest.json"
tar -czf "$task_root/k1-walk-04-evidence.tar.gz" --exclude=converted -C "$task_root/evidence/k1-walk-04" .
JOB
nohup bash "$task_root/k1-walk-04-job.sh" > "$task_root/k1-walk-04.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/k1-walk-04.pid"
echo "Unloaded actor diagnostic launched."
