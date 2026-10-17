#!/usr/bin/env bash
# Run through brev exec @file. Detach once: Brev may retry nonzero SSH commands.
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
mkdir -p "$task_root"
if ! mkdir "$task_root/driver-install.started" 2>/dev/null; then
  echo "Driver install already launched; inspect driver-install.log and .exit."
  exit 0
fi
cat > "$task_root/install-driver-job.sh" <<'JOB'
#!/usr/bin/env bash
set -euo pipefail
task_root="$HOME/workspace/k1-runtime"
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/driver-install.exit"' EXIT
test -d "/lib/modules/$(uname -r)/build"
date -u
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nvidia-driver-580-open
sudo dkms status
modinfo -F version nvidia
date -u
echo "Driver installed. OS reboot must be performed separately after log review."
JOB
nohup bash "$task_root/install-driver-job.sh" > "$task_root/driver-install.log" 2>&1 < /dev/null &
echo "$!" > "$task_root/driver-install.pid"
echo "Driver install launched; PID $(cat "$task_root/driver-install.pid")."
