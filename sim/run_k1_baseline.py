#!/usr/bin/env python3
"""Run official K1 policy in MuJoCo with recorded, scripted velocity commands.

This is a locomotion integration diagnostic, NOT vision-guided delivery, training,
or a physical hardware test. Upstream policy and control code remain unchanged.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "sim/vendor/booster_deploy"
sys.path.insert(0, str(DEPLOY))

import mujoco
import numpy as np
import torch

from booster_deploy.controllers.mujoco_controller import MujocoController
from tasks.locomotion.robots.k1 import K1WalkTaskCfg


class ScriptedCommandController(MujocoController):
    def update_vel_command(self):
        # Suppress interactive stdin polling only; the trial owns velocity commands.
        pass


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output, duration, speed, render):
    if duration <= 4 or duration > 120 or not 0 <= speed <= 0.5:
        raise ValueError("Diagnostic requires 4 < duration <= 120 s and 0 <= speed <= 0.5 m/s")
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    torch.manual_seed(0)
    cfg = K1WalkTaskCfg()
    checkpoint = DEPLOY / "tasks/locomotion/robots/k1/models/k1_walk.pt"
    cfg.policy.checkpoint_path = str(checkpoint)
    # Upstream defaults supply policy dt, PD gains, limits and initial posture.
    controller = ScriptedCommandController(cfg)
    model, data = controller.mj_model, controller.mj_data
    joint_names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(1, model.njnt)]
    if joint_names != cfg.robot.joint_names:
        raise RuntimeError("MuJoCo joint order does not match deployment robot order")
    for i, joint in enumerate(cfg.robot.joint_names):
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
        if int(model.actuator_trnid[i, 0]) != joint_id:
            raise RuntimeError("Actuator order does not match deployment robot order")

    manifest = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evidence_kind": "mujoco_scripted_velocity_locomotion_diagnostic",
        "vision_guided": False, "training_performed": False, "hardware_tested": False,
        "payload_present": False, "delivery_success": None,
        "command_source": "scripted: stand 2 s, forward until last 2 s, stop 2 s",
        "duration_requested_s": duration, "forward_command_m_s": speed,
        "seed": 0, "platform": platform.platform(),
        "versions": {"python": platform.python_version(), "mujoco": mujoco.__version__,
                     "torch": torch.__version__, "numpy": np.__version__},
        "upstream_lock": json.loads((ROOT / "sim/upstream-lock.json").read_text()),
        "checkpoint": {"path": str(checkpoint.relative_to(ROOT)), "sha256": sha256(checkpoint)},
        "runner_sha256": sha256(Path(__file__)),
        "model_sha256": sha256(Path(controller._expand_assets_placeholder(cfg.robot.mjcf_path))),
        "policy_dt_s": cfg.policy_dt, "physics_dt_s": float(model.opt.timestep),
        "joint_order": joint_names, "joint_order_verified": True,
        "actor_observations": ["body_angular_velocity", "projected_gravity", "velocity_command",
                               "joint_position_offsets", "scaled_joint_velocities", "previous_action"],
        "evaluation_only": ["world_position", "world_displacement", "base_height"],
        "render_requested": render, "render_error": None,
        "robotics_claim": "single unloaded locomotion diagnostic only",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    renderer = None
    writer = None
    frames = 0
    if render:
        try:
            import imageio.v2 as imageio
            from PIL import Image
            renderer = mujoco.Renderer(model, height=480, width=640)
            writer = imageio.get_writer(str(output / "trial.mp4"), fps=25, codec="libx264")
        except Exception as exc:
            manifest["render_error"] = type(exc).__name__ + ": " + str(exc)
            if renderer is not None:
                renderer.close()
            renderer = None
            if writer is not None:
                writer.close()
            writer = None

    controller.update_state()
    controller.start()
    initial = data.qpos[:3].copy()
    minimum_height = float(initial[2])
    maximum_tilt = 0.0
    termination = "completed_requested_duration"
    began = time.monotonic()
    with (output / "trajectory.csv").open("w", newline="") as handle:
        csv_writer = csv.writer(handle)
        csv_writer.writerow(["sim_time_s", "world_x_m", "world_y_m", "base_z_m", "tilt_deg",
                             "command_vx_m_s", "max_abs_torque_nm"] + ["q_" + j for j in joint_names])
        try:
            for step in range(round(duration / cfg.policy_dt)):
                t = float(data.time)
                controller.vel_command.lin_vel_x = speed if 2.0 <= t < duration - 2.0 else 0.0
                controller.update_state()
                targets = controller.policy_step()
                if not controller.is_running:
                    termination = "upstream_fall_fallback"
                    break
                if not torch.isfinite(targets).all():
                    termination = "nonfinite_policy_output"
                    break
                controller.ctrl_step(targets)
                if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                    termination = "nonfinite_physics_state"
                    break
                w, x, y, z = data.qpos[3:7]
                tilt = float(np.degrees(np.arccos(np.clip(1 - 2 * (x*x + y*y), -1, 1))))
                maximum_tilt = max(maximum_tilt, tilt)
                minimum_height = min(minimum_height, float(data.qpos[2]))
                csv_writer.writerow([float(data.time), *data.qpos[:3], tilt,
                                     controller.vel_command.lin_vel_x, float(np.max(np.abs(data.ctrl))),
                                     *data.qpos[7:]])
                if renderer is not None and step % 2 == 0:
                    camera = mujoco.MjvCamera()
                    camera.lookat[:] = data.qpos[:3]
                    camera.distance = 2.2
                    camera.azimuth = 140
                    camera.elevation = -15
                    renderer.update_scene(data, camera=camera)
                    frame = renderer.render()
                    writer.append_data(frame)
                    if frames == 0 or step % 250 == 0:
                        Image.fromarray(frame).save(output / f"frame-{step:05d}.png")
                    frames += 1
                if data.qpos[2] < 0.30 or tilt > 60:
                    termination = "height_or_tilt_failure"
                    break
        except Exception as exc:
            termination = "runtime_error"
            manifest["runtime_error"] = type(exc).__name__ + ": " + str(exc)
        finally:
            controller.stop()
            if writer is not None:
                writer.close()
            if renderer is not None:
                renderer.close()

    manifest.update({
        "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "termination": termination, "elapsed_sim_s": float(data.time),
        "wall_time_s": time.monotonic() - began,
        "initial_position_m": initial.tolist(), "final_position_m": data.qpos[:3].tolist(),
        "forward_displacement_m": float(data.qpos[0] - initial[0]),
        "minimum_base_height_m": minimum_height, "maximum_base_tilt_deg": maximum_tilt,
        "video_frames": frames,
        "artifacts": {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size}
                      for p in output.iterdir() if p.name != "manifest.json"},
    })
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({key: manifest[key] for key in ["termination", "elapsed_sim_s", "forward_displacement_m",
                                                   "minimum_base_height_m", "maximum_base_tilt_deg",
                                                   "video_frames", "render_error"]}, indent=2))
    return 0 if termination == "completed_requested_duration" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--duration", type=float, default=15.0)
    parser.add_argument("--speed", type=float, default=0.2)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    return run(args.output, args.duration, args.speed, args.render)


if __name__ == "__main__":
    raise SystemExit(main())
