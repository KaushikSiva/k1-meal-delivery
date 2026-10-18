#!/usr/bin/env bash
set -euo pipefail
task_root=/home/ubuntu/workspace/k1-runtime
live_root="$task_root/live-desktop-01"
mkdir -p "$live_root"
export DISPLAY=:99
if ! xdpyinfo -display :99 >/dev/null 2>&1; then
  nohup Xvfb :99 -screen 0 1600x900x24 -ac -nolisten tcp > "$live_root/xvfb.log" 2>&1 < /dev/null &
  echo $! > "$live_root/xvfb.pid"
  for attempt in {1..50}; do xdpyinfo -display :99 >/dev/null 2>&1 && break; sleep .1; done
fi
xdpyinfo -display :99 >/dev/null
if ! test -f "$live_root/openbox.pid" || ! kill -0 "$(cat "$live_root/openbox.pid")" 2>/dev/null; then
  nohup openbox > "$live_root/openbox.log" 2>&1 < /dev/null &
  echo $! > "$live_root/openbox.pid"
fi
if ! test -f "$live_root/vnc.pid" || ! kill -0 "$(cat "$live_root/vnc.pid")" 2>/dev/null; then
  nohup x11vnc -display :99 -localhost -rfbport 5900 -forever -shared -nopw -noxdamage > "$live_root/vnc.log" 2>&1 < /dev/null &
  echo $! > "$live_root/vnc.pid"
fi
if ! test -f "$live_root/web.pid" || ! kill -0 "$(cat "$live_root/web.pid")" 2>/dev/null; then
  nohup websockify --web=/usr/share/novnc 127.0.0.1:6080 127.0.0.1:5900 > "$live_root/web.log" 2>&1 < /dev/null &
  echo $! > "$live_root/web.pid"
fi
if ! test -f "$live_root/isaac.pid" || ! kill -0 "$(cat "$live_root/isaac.pid")" 2>/dev/null; then
  cd "$task_root/project"
  export ACCEPT_EULA=Y OMNI_KIT_ACCEPT_EULA=YES
  nohup "$task_root/.venv/bin/python" sim/run_k1_hand_carry_isaac.py \
    --output "$live_root/scene-$(date -u +%Y%m%dT%H%M%S)" --duration 15 --speed .4 --interactive \
    > "$live_root/isaac.log" 2>&1 < /dev/null &
  echo $! > "$live_root/isaac.pid"
fi
echo "Desktop services started; inspect $live_root/isaac.log for TABLESIDE_LIVE_READY."
