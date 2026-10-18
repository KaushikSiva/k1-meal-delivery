"""LIVE interactive demo: Codex's sensor-only loaded navigation (unchanged) in MuJoCo's viewer.

Run on the Mac (macOS needs mjpython for the viewer):
  sim/.venv/bin/mjpython demo/live_mujoco.py            # loaded05 configuration, real time
  sim/.venv/bin/mjpython demo/live_mujoco.py --speed 2  # 2x faster than real time
Judges can orbit (left-drag), pan (right-drag) and zoom (scroll) while it runs. Nothing about the
robot, perception or control is changed: this wraps the controller step to sync the viewer and pace
playback. Outputs (videos, logs) still go to --output exactly as the original runner writes them.
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pre = argparse.ArgumentParser(add_help=False)
pre.add_argument("--speed", type=float, default=1.0)
pre.add_argument("--output", type=Path, default=None)
known, rest = pre.parse_known_args()
out = known.output or Path(f"/tmp/k1-live-{int(time.time())}")

import mujoco  # noqa: E402
import mujoco.viewer  # noqa: E402
import sim.run_k1_sensor_navigation as runner  # noqa: E402  (adds booster_deploy to sys.path)
from sim.k1_hand_controller import HandSensorController  # noqa: E402

_state = {"viewer": None, "t0": None, "sim0": None}


def _wrap(cls):
    orig = cls.ctrl_step

    def live_ctrl_step(self, *a, **k):
        r = orig(self, *a, **k)
        _show(self)
        return r
    cls.ctrl_step = live_ctrl_step


def _show(self):
    if _state["viewer"] is None:
        v = mujoco.viewer.launch_passive(self.mj_model, self.mj_data)
        v.cam.distance, v.cam.azimuth, v.cam.elevation = 4.5, 200, -22
        _state.update(viewer=v, t0=time.monotonic(), sim0=float(self.mj_data.time))
    v = _state["viewer"]
    v.cam.lookat[:] = self.mj_data.qpos[:3]  # follow the robot (users can still orbit/zoom)
    v.sync()
    target = (float(self.mj_data.time) - _state["sim0"]) / known.speed
    lag = target - (time.monotonic() - _state["t0"])
    if lag > 0:
        time.sleep(lag)


# Both controllers override ctrl_step without calling the base, so wrap each one.
_wrap(runner.SensorController)
_wrap(HandSensorController)

LOADED05 = ["--hand-carried", "--known-load-depth-mask", "--carry-command-guard", "--head-pitch", "-0.2",
            "--prediction-scale", "0.5", "--walk-speed", "0.4", "--settle-seconds", "2", "--duration", "60",
            "--tracking-evaluator"]
sys.argv = [sys.argv[0], "--output", str(out)] + (rest if rest else LOADED05)
print(f"LIVE demo → {out}  (args: {' '.join(sys.argv[3:])})", flush=True)
runner.main()
if _state["viewer"] is not None:
    print("Run finished — close the viewer window to exit.", flush=True)
    while _state["viewer"].is_running():
        time.sleep(0.1)
