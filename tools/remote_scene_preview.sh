#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
test "$(cat "$task_root/runtime-reconcile-02.exit")" = 0
if ! mkdir "$task_root/scene-preview-04.started" 2>/dev/null; then
  echo "Scene preview already launched; inspect scene-preview.log and .exit."
  exit 0
fi
cat > "$task_root/scene-preview-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/scene-preview-04.exit"' EXIT
mkdir -p "$task_root/project"
tar -xzf "$task_root/cafe-preview-04.tar.gz" -C "$task_root/project"
cd "$task_root/project"
source "$task_root/.venv/bin/activate"
export OMNI_KIT_ACCEPT_EULA=YES
python tools/fetch_cafe_assets.py
# The unchanged runtime already passed smoke-02; don't rerun it for visual edits.
python -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"] == "passed"' "$task_root/evidence/smoke-02/manifest.json"
python sim/render_cafe.py --output "$task_root/evidence/cafe-04"
python -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"] == "rendered"' "$task_root/evidence/cafe-04/manifest.json"
JOB
nohup bash "$task_root/scene-preview-job.sh" > "$task_root/scene-preview-04.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/scene-preview-04.pid"
echo "Scene preview launched."
