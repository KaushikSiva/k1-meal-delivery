#!/usr/bin/env python3
"""DIAGNOSTIC trial: official K1 walking policy (k1_walk.pt, unchanged) commanded by Claude's
AutonomySession (executive + follower) from K1 head-camera RGB-D rendered in MuJoCo.

PRIVILEGED: pose, base attitude/height and twist come from simulator state through Codex's
DiagnosticObservationAdapter (sim_gt). Perception = depth-geometry tables + restricted placard
diagnostic. No payload. Not deployable delivery evidence.
"""
import argparse, json, sys, time, hashlib
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT = Path.home() / "workspace/k1-meal-delivery"
DEPLOY = ROOT / "sim/vendor/booster_deploy"
sys.path[:0] = [str(ROOT), str(DEPLOY)]
import mujoco, torch
from booster_deploy.controllers.mujoco_controller import MujocoController
from tasks.locomotion.robots.k1 import K1WalkTaskCfg
from sim.k1_observation import sensor_spec, DiagnosticObservationAdapter
from autonomy.contracts import DeliveryTask, OccupancyGrid, Region
from autonomy.grounding import parse_instruction
from autonomy.session import AutonomySession
from perception.tabletop import TabletopDetector, CombinedDetector
from perception.detectors import BoxLifter
from perception.placard import PlacardReader, make_placard_png

TABLES = [  # (number, center xy, half sizes, placard facing yaw) — static scene, also the operator floor plan
    ("3", (4.0, 0.0), (0.4, 0.5)),
    ("1", (2.6, 2.2), (0.4, 0.5)),
]
TOP = 0.75


def qmul(a, b):
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return [w1*w2-x1*x2-y1*y2-z1*z2, w1*x2+x1*w2+y1*z2-z1*y2, w1*y2-x1*z2+y1*w2+z1*x2, w1*z2+x1*y2-y1*x2+z1*w2]


def build_spec(tmp: Path):
    spec = sensor_spec(ROOT / "sim/vendor/booster_assets/robots/K1/K1_22dof.xml")
    wb = spec.worldbody
    wb.add_light(pos=[2, 0, 4], dir=[0, 0, -1], diffuse=[0.7, 0.7, 0.7])
    c = np.cos(-np.pi / 4)
    q = qmul([c, 0, -c, 0], [c, 0, 0, -c])  # plane normal -> -x, PNG top up (validated in tests)
    for num, (x, y), (hx, hy) in TABLES:
        png = tmp / f"placard_{num}.png"; make_placard_png(num, png)
        spec.add_texture(name=f"t{num}", type=mujoco.mjtTexture.mjTEXTURE_2D, file=str(png))
        m = spec.add_material(name=f"m{num}"); m.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = f"t{num}"
        wb.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, pos=[x, y, TOP / 2], size=[hx, hy, TOP / 2], rgba=[0.6, 0.45, 0.3, 1])
        b = wb.add_body(name=f"placard{num}", pos=[x - hx - 0.01, y, TOP + 0.15])
        b.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0.1, 0.1, 0.01], quat=q, material=f"m{num}",
                   contype=0, conaffinity=0)
    return spec


def floor_plan(res=0.1, bounds=(-1.0, -3.0, 7.0, 4.0)):
    x0, y0, x1, y1 = bounds
    W, H = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    data = np.zeros((H, W), np.uint8)
    data[0, :] = data[-1, :] = data[:, 0] = data[:, -1] = OccupancyGrid.OCCUPIED
    g = OccupancyGrid(data, res, (x0, y0))
    for _, (x, y), (hx, hy) in TABLES:  # furniture footprint known from the floor plan (operator prior)
        r0, c0 = g.world_to_cell((x - hx, y - hy)); r1, c1 = g.world_to_cell((x + hx, y + hy))
        data[r0:r1 + 1, c0:c1 + 1] = OccupancyGrid.OCCUPIED
    return g


class SceneController(MujocoController):
    def __init__(self, cfg, spec):
        super().__init__(cfg)
        qpos0 = self.mj_data.qpos.copy()
        nq, nu = self.mj_model.nq, self.mj_model.nu
        m = spec.compile()
        assert m.nq == nq and m.nu == nu, "scene overlay changed joints/actuators"
        m.opt.timestep = self.cfg.mujoco.physics_dt
        self.mj_model, self.mj_data = m, mujoco.MjData(m)
        self.mj_data.qpos[:] = qpos0
        mujoco.mj_forward(m, self.mj_data)
        self._ghost_mj_data = mujoco.MjData(m); self._ghost_mj_data.qpos[:] = qpos0
        mujoco.mj_forward(m, self._ghost_mj_data)

    def update_vel_command(self):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-s", type=float, default=120.0)
    ap.add_argument("--cam-hz", type=float, default=5.0)
    ap.add_argument("--instruction", default="deliver the pizza and drink to table 3")
    ap.add_argument("--start-yaw", type=float, default=0.0, help="initial heading (rad)")
    ap.add_argument("--deadband", type=float, default=0.0, help="opt-in min walk command (diagnostic)")
    a = ap.parse_args()
    a.out = a.out.resolve()  # MuJoCo resolves texture files relative to the model dir
    a.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1); torch.manual_seed(0)
    cfg = K1WalkTaskCfg()
    cfg.policy.checkpoint_path = str(DEPLOY / "tasks/locomotion/robots/k1/models/k1_walk.pt")
    cfg.mujoco.init_quat = [float(np.cos(a.start_yaw / 2)), 0.0, 0.0, float(np.sin(a.start_yaw / 2))]
    ctrl = SceneController(cfg, build_spec(a.out))
    model, data = ctrl.mj_model, ctrl.mj_data
    adapter = DiagnosticObservationAdapter(model, diagnostic=True)
    eval_r = mujoco.Renderer(model, height=360, width=480)
    grid = floor_plan()
    task = DeliveryTask(a.instruction, parse_instruction(a.instruction), 0.0, a.max_s)
    det = CombinedDetector(TabletopDetector(), BoxLifter(PlacardReader()))
    from autonomy.executive import ExecutiveConfig
    from navigation.follower import FollowerLimits
    cfgx, lim = None, None
    if a.deadband > 0:  # DIAGNOSTIC: compensate the unloaded k1_walk low-speed deadband; final cap raised to match
        cfgx = ExecutiveConfig(final_speed=a.deadband, approach_speed=max(0.35, a.deadband), search_speed=max(0.35, a.deadband))
        lim = FollowerLimits(min_walk_cmd=a.deadband, final_accel=0.25)
    sess = AutonomySession(task, grid, det, [Region("dining", (3.3, 1.0), 2.0, ("dining",))], config=cfgx, limits=lim, deployable=False)
    import imageio.v2 as iio
    vid_eval = iio.get_writer(str(a.out / "evaluator.mp4"), fps=10, codec="libx264")
    vid_cam = iio.get_writer(str(a.out / "robot_camera.mp4"), fps=10, codec="libx264")
    ctrl.update_state(); ctrl.start()
    traj, cam_period, next_cam, t0 = [], 1.0 / a.cam_hz, 0.0, time.monotonic()
    termination = "max_time"
    frames_saved = 0
    try:
        while data.time < a.max_s:
            t = float(data.time)
            obs = None
            if t >= next_cam:
                obs = adapter.observe(data); next_cam += cam_period
            vx, vy, wz = sess.tick(obs, t, cfg.policy_dt) if t >= 2.0 else (0.0, 0.0, 0.0)  # stand 2 s
            ctrl.vel_command.lin_vel_x, ctrl.vel_command.lin_vel_y, ctrl.vel_command.ang_vel_yaw = vx, vy, wz
            ctrl.update_state()
            targets = ctrl.policy_step()
            if not ctrl.is_running:
                termination = "upstream_fall_fallback"; break
            ctrl.ctrl_step(targets)
            w, x, y, z = data.qpos[3:7]
            tilt = float(np.degrees(np.arccos(np.clip(1 - 2 * (x * x + y * y), -1, 1))))
            traj.append([t, *data.qpos[:3], tilt, vx, vy, wz, sess.executive.state.value])
            if data.qpos[2] < 0.30 or tilt > 60:
                termination = "fall"; break
            if obs is not None and int(t * a.cam_hz) % 2 == 0:  # 2.5 Hz video
                cam = obs.camera.rgb
                cam_s = cam[::2, ::2] if False else cam
                vid_cam.append_data(cam_s)
                c = mujoco.MjvCamera(); c.lookat[:] = [(data.qpos[0] + 4.0) / 2, data.qpos[1] / 2 + 0.6, 0.4]
                c.distance, c.azimuth, c.elevation = 5.5, -70, -28  # side view: robot + table 3 + table 1
                eval_r.update_scene(data, camera=c); vid_eval.append_data(eval_r.render())
                if frames_saved < 200 and int(t) % 5 == 0 and abs(t - round(t)) < 0.11:
                    iio.imwrite(a.out / f"robot_camera_t{int(t):03d}.png", cam)
                    iio.imwrite(a.out / f"evaluator_t{int(t):03d}.png", eval_r.render()); frames_saved += 1
            if sess.done and t > 2.0:
                termination = "autonomy_terminal"
                # hold 2 s standing to show the stable stop
                for _ in range(int(2.0 / cfg.policy_dt)):
                    ctrl.vel_command.lin_vel_x = ctrl.vel_command.lin_vel_y = ctrl.vel_command.ang_vel_yaw = 0.0
                    ctrl.update_state(); ctrl.ctrl_step(ctrl.policy_step())
                eval_r.update_scene(data, camera=c); iio.imwrite(a.out / "evaluator_final.png", eval_r.render())
                iio.imwrite(a.out / "robot_camera_final.png", adapter.observe(data).camera.rgb)
                break
    finally:
        ctrl.stop(); vid_eval.close(); vid_cam.close()
    np.savetxt(a.out / "trajectory.csv", np.array([r[:8] for r in traj], float), delimiter=",",
               header="t,x,y,z,tilt_deg,cmd_vx,cmd_vy,cmd_wz", comments="")
    (a.out / "states.txt").write_text("\n".join(f"{r[0]:.2f} {r[8]}" for r in traj[::25]))
    xy = data.qpos[:2].copy()
    tx, ty = TABLES[0][1]
    edge = float(np.linalg.norm(np.clip(xy, [tx - 0.4, ty - 0.5], [tx + 0.4, ty + 0.5]) - xy))
    res = {
        "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evidence_kind": "mujoco_privileged_diagnostic_autonomy_trial",
        "privileged_inputs": ["map_pose(sim_gt)", "base_attitude_height", "base_twist", "floor_plan_furniture_footprints"],
        "perception": "TabletopDetector(depth) + PlacardReader(RGB, restricted placard diagnostic)",
        "payload_present": False, "instruction": a.instruction, "deadband_compensation": a.deadband,
        "termination": termination, "outcome": None if sess.outcome is None else sess.outcome.value,
        "sim_time_s": float(data.time), "wall_s": time.monotonic() - t0,
        "final_xy": xy.tolist(), "dist_to_table3_edge_m": edge,
        "max_tilt_deg": float(max(r[4] for r in traj)) if traj else None,
        "events": [f"{e.t:.1f} {e.state}: {e.msg}" for e in sess.events],
        "checkpoint_sha256": hashlib.sha256((DEPLOY / "tasks/locomotion/robots/k1/models/k1_walk.pt").read_bytes()).hexdigest(),
    }
    (a.out / "result.json").write_text(json.dumps(res, indent=2))
    print(json.dumps({k: res[k] for k in ("termination", "outcome", "sim_time_s", "wall_s", "final_xy", "dist_to_table3_edge_m", "max_tilt_deg")}, indent=2))


if __name__ == "__main__":
    main()
