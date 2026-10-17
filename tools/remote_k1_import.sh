#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
test "$(cat "$task_root/cafe-rgbd-01.exit")" = 0
if ! mkdir "$task_root/k1-import-03.started" 2>/dev/null; then
  echo "Import already launched; inspect k1-import-03.log and .exit."
  exit 0
fi
cat > "$task_root/k1-import-03-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/k1-import-03.exit"' EXIT
tar -xzf "$task_root/k1-import-03-source.tar.gz" -C "$task_root/project"
cd "$task_root/project"
source "$task_root/.venv/bin/activate"
export OMNI_KIT_ACCEPT_EULA=YES
python sim/import_k1_isaac.py --output "$task_root/evidence/k1-import-03"
python -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"]=="tested"' "$task_root/evidence/k1-import-03/manifest.json"
tar -czf "$task_root/k1-import-03-evidence.tar.gz" --exclude=converted -C "$task_root/evidence/k1-import-03" .
JOB
nohup bash "$task_root/k1-import-03-job.sh" > "$task_root/k1-import-03.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/k1-import-03.pid"
echo "K1 import diagnostic launched."
