#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
if ! mkdir "$task_root/cafe-rgbd-01.started" 2>/dev/null; then
  echo "Capture already launched; inspect cafe-rgbd-01.log and .exit."
  exit 0
fi
cat > "$task_root/cafe-rgbd-01-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/cafe-rgbd-01.exit"' EXIT
tar -xzf "$task_root/cafe-rgbd-01-source.tar.gz" -C "$task_root/project"
cd "$task_root/project"
source "$task_root/.venv/bin/activate"
export OMNI_KIT_ACCEPT_EULA=YES
python sim/capture_cafe_rgbd.py --output "$task_root/evidence/cafe-rgbd-01"
python -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"]=="captured"' "$task_root/evidence/cafe-rgbd-01/manifest.json"
tar -czf "$task_root/cafe-rgbd-01-evidence.tar.gz" -C "$task_root/evidence/cafe-rgbd-01" .
JOB
nohup bash "$task_root/cafe-rgbd-01-job.sh" > "$task_root/cafe-rgbd-01.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/cafe-rgbd-01.pid"
echo "Capture launched."
