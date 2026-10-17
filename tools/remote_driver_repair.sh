#!/usr/bin/env bash
# Targeted recovery for the recorded 565-extra / 580-gl packaging file conflict.
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
test "$(cat "$task_root/driver-install.exit")" = 100
if ! mkdir "$task_root/driver-repair.started" 2>/dev/null; then
  echo "Driver repair already launched; inspect driver-repair.log and .exit."
  exit 0
fi
cat > "$task_root/repair-driver-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/driver-repair.exit"' EXIT
date -u
sudo dpkg --remove libnvidia-extra-565
sudo env DEBIAN_FRONTEND=noninteractive apt-get --fix-broken install -y --no-install-recommends nvidia-driver-580-open libnvidia-gl-580
sudo dpkg --audit
sudo dkms status
modinfo -F version nvidia
date -u
echo "Repaired driver installation. Reboot separately after reviewing log."
JOB
nohup bash "$task_root/repair-driver-job.sh" > "$task_root/driver-repair.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/driver-repair.pid"
echo "Driver repair launched; PID $(cat "$task_root/driver-repair.pid")."
