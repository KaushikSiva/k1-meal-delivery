"""SOFTWARE TEST FIXTURE ONLY — not a simulator, not robot evidence.

A ray-cast box room that emits contract-shaped Observations, a fixture "2D detector" that
stands in for a learned detector + OCR (reads table numbers only within `ocr_range`), and a
kinematic point-robot controller that honors AutonomyCommands (speed limits, scan, hold,
expiry) and reports BLOCKED when a hidden obstacle is on the path.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from autonomy.contracts import (
    AutonomyCommand,
    CameraFrame,
    CameraIntrinsics,
    CommandKind,
    ControlFeedback,
    FeedbackStatus,
    LocalizationStatus,
    Observation,
    OccupancyGrid,
    Pose2D,
    PoseEstimate,
    Provenance,
)
from perception.detectors import BoxLifter, Detection2D

CAM_HEIGHT = 1.1
CAM_PITCH_DEG = 15.0


@dataclass
class Box:
    seg_id: int
    label: str
    lo: np.ndarray
    hi: np.ndarray
    attributes: dict[str, str] = field(default_factory=dict)
    in_map: bool = True  # False = obstacle not in the prior map (discovered at runtime)
    visible: bool = True
    solid: bool = True  # False: occludes the camera but the robot can pass (e.g. a passer-by)

    @property
    def center(self):
        return (self.lo + self.hi) / 2


def T_base_camera(height=CAM_HEIGHT, pitch_deg=CAM_PITCH_DEG) -> np.ndarray:
    p = np.deg2rad(pitch_deg)
    fwd = np.array([np.cos(p), 0.0, -np.sin(p)])
    right = np.array([0.0, -1.0, 0.0])
    down = np.cross(fwd, right)
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = right, down, fwd, [0, 0, height]
    return T


class FakeRoom:
    def __init__(self, boxes: list[Box], bounds=(0.0, 0.0, 10.0, 8.0), res=0.1, start=Pose2D(1.0, 1.0, 0.0)):
        self.boxes = boxes
        self.bounds = bounds
        self.res = res
        self.K = CameraIntrinsics.from_fovy(58, 96, 72)
        self.T_bc = T_base_camera()
        self.true_pose = start
        self.t = 0.0
        self.twist = np.zeros(3)
        # Localization model: estimate = truth + bias; status/sigma settable by tests.
        self.pose_bias = np.zeros(3)
        self.pose_sigma = 0.03
        self.pose_status = LocalizationStatus.OK
        self.camera_on = True
        self.pose_on = True

    # ---------------------------------------------------------------- map
    def grid(self) -> OccupancyGrid:
        x0, y0, x1, y1 = self.bounds
        W, H = int(round((x1 - x0) / self.res)), int(round((y1 - y0) / self.res))
        data = np.zeros((H, W), np.uint8)
        data[0, :] = data[-1, :] = data[:, 0] = data[:, -1] = OccupancyGrid.OCCUPIED
        g = OccupancyGrid(data, self.res, (x0, y0))
        for b in self.boxes:
            if b.in_map:
                r0, c0 = g.world_to_cell(b.lo[:2])
                r1, c1 = g.world_to_cell(b.hi[:2])
                data[max(r0, 0):r1 + 1, max(c0, 0):c1 + 1] = OccupancyGrid.OCCUPIED
        return g

    # ---------------------------------------------------------------- sensing
    def _render(self):
        K = self.K
        T = self.true_pose.matrix() @ self.T_bc
        us, vs = np.meshgrid(np.arange(K.width), np.arange(K.height))
        d_w = np.stack([(us - K.cx) / K.fx, (vs - K.cy) / K.fy, np.ones(us.shape)], -1) @ T[:3, :3].T
        o = T[:3, 3]
        depth = np.full((K.height, K.width), np.inf)
        seg = np.zeros((K.height, K.width), np.int32)
        with np.errstate(divide="ignore", invalid="ignore"):
            tf = -o[2] / d_w[..., 2]
            floor = (tf > 0) & np.isfinite(tf)
            depth[floor] = tf[floor]
            for b in self.boxes:
                if not b.visible:
                    continue
                t1, t2 = (b.lo - o) / d_w, (b.hi - o) / d_w
                tmin = np.nanmax(np.minimum(t1, t2), -1)
                tmax = np.nanmin(np.maximum(t1, t2), -1)
                hit = (tmax >= tmin) & (tmin > 0) & (tmin < depth)
                depth[hit], seg[hit] = tmin[hit], b.seg_id
        depth[~np.isfinite(depth) | (depth > 15)] = 0
        return depth.astype(np.float32), seg

    def observe(self) -> Observation:
        cam = None
        if self.camera_on:
            depth, seg = self._render()
            cam = CameraFrame(
                timestamp=self.t, intrinsics=self.K, T_base_camera=self.T_bc, depth=depth,
                segmentation=seg, segment_labels={b.seg_id: b.label for b in self.boxes},
                segmentation_provenance=Provenance.SIM_PRIVILEGED,
            )
        pose = None
        if self.pose_on:
            p = self.true_pose
            pose = PoseEstimate(
                Pose2D(p.x + self.pose_bias[0], p.y + self.pose_bias[1], p.yaw + self.pose_bias[2]),
                np.diag([self.pose_sigma**2, self.pose_sigma**2, (self.pose_sigma / 2) ** 2]),
                self.t, "fixture_odom", Provenance.ESTIMATED, self.pose_status,
            )
        return Observation(self.t, cam, pose, base_twist=self.twist.copy())


def fixture_detector_2d(room: FakeRoom, ocr_range: float = 2.0, labels=("table", "person", "counter")):
    """Stands in for a learned detector: uses the fixture's own render masks (test-only) and
    exposes attributes like a table-number OCR that only works up close."""

    def detect(obs: Observation) -> list[Detection2D]:
        cam = obs.camera
        out = []
        by_id = {b.seg_id: b for b in room.boxes}
        for sid in np.unique(cam.segmentation):
            b = by_id.get(int(sid))
            if b is None or b.label not in labels:
                continue
            mask = cam.segmentation == sid
            if mask.sum() < 15:
                continue
            vs, us = np.nonzero(mask)
            p = room.true_pose.xy()
            dist = np.linalg.norm(np.clip(p, b.lo[:2], b.hi[:2]) - p)  # placard on the table edge
            attrs = {}
            for k, v in b.attributes.items():
                if k != "table_number" or dist <= ocr_range:
                    attrs[k] = (v, 0.9)
            out.append(Detection2D(b.label, (int(us.min()), int(vs.min()), int(us.max()), int(vs.max())), 0.85,
                                   attrs, mask=mask))
        return out

    return BoxLifter(detect)


class KinematicController:
    """Point robot following AutonomyCommands. dt-stepped; reports feedback each tick."""

    def __init__(self, room: FakeRoom, dt: float = 0.2, accel: float = 0.5, wz_max: float = 0.8):
        self.room, self.dt, self.accel, self.wz_max = room, dt, accel, wz_max
        self.cmd: AutonomyCommand | None = None
        self.wp = 0
        self.scan_left = 0.0
        self.speed = 0.0
        self.max_speed_seen = 0.0

    def _blocked_by_hidden(self, xy) -> Box | None:
        for b in self.room.boxes:
            if not b.in_map and b.solid and (b.lo[0] - 0.3 <= xy[0] <= b.hi[0] + 0.3) and (b.lo[1] - 0.3 <= xy[1] <= b.hi[1] + 0.3):
                return b
        return None

    def step(self, cmd: AutonomyCommand) -> ControlFeedback:
        r = self.room
        if self.cmd is None or cmd.issued_at != self.cmd.issued_at:
            self.cmd, self.wp, self.scan_left = cmd, 0, cmd.scan_yaw
        r.t += self.dt
        p = r.true_pose
        status, msg, blocked_at = FeedbackStatus.RUNNING, "", None
        vx = wz = 0.0
        if r.t > cmd.expires_at or cmd.kind in (CommandKind.HOLD, CommandKind.STOP):
            self.speed = max(0.0, self.speed - self.accel * self.dt)
            # decelerate in place (point robot): residual speed shows up in twist only
            status = FeedbackStatus.REACHED if cmd.kind == CommandKind.HOLD else FeedbackStatus.RUNNING
            vx = self.speed
        elif cmd.kind == CommandKind.SCAN:
            step = np.clip(self.scan_left, -self.wz_max * self.dt, self.wz_max * self.dt)
            self.scan_left -= step
            r.true_pose = Pose2D(p.x, p.y, p.yaw + step)
            wz = step / self.dt
            if abs(self.scan_left) < 1e-6:
                status = FeedbackStatus.REACHED
        else:  # NAVIGATE / FINAL_APPROACH: follow path (or straight to goal), then align yaw
            pts = list(cmd.path or []) + [tuple(cmd.goal_pose.xy())]
            while self.wp < len(pts) - 1 and np.linalg.norm(np.asarray(pts[self.wp]) - r.pose_bias[:2] - p.xy()) < 1e-3:
                self.wp += 1  # already on this waypoint
            # Convert path from estimated map frame to truth by removing bias (fixture shortcut).
            target = np.asarray(pts[min(self.wp, len(pts) - 1)]) - r.pose_bias[:2]
            d = target - p.xy()
            dist = float(np.linalg.norm(d))
            remaining = dist + sum(np.linalg.norm(np.subtract(pts[i + 1], pts[i])) for i in range(self.wp, len(pts) - 1))
            vmax = min(cmd.max_speed, np.sqrt(2 * self.accel * max(remaining, 0.0)))
            self.speed = min(vmax, self.speed + self.accel * self.dt)
            if dist < 1e-3 and self.wp >= len(pts) - 1:
                dyaw = float(np.angle(np.exp(1j * (cmd.goal_pose.yaw - r.pose_bias[2] - p.yaw))))
                step = np.clip(dyaw, -self.wz_max * self.dt, self.wz_max * self.dt)
                r.true_pose = Pose2D(p.x, p.y, p.yaw + step)
                wz, self.speed = step / self.dt, 0.0
                if abs(dyaw) < 0.05:
                    status = FeedbackStatus.REACHED
            else:
                adv = min(self.speed * self.dt, dist)
                nxt = p.xy() + d / max(dist, 1e-9) * adv
                hb = self._blocked_by_hidden(nxt)
                if hb is not None:
                    self.speed = 0.0
                    near = np.clip(p.xy(), hb.lo[:2], hb.hi[:2])
                    status, msg, blocked_at = FeedbackStatus.BLOCKED, f"obstacle {hb.label}", tuple(near + r.pose_bias[:2])
                else:
                    heading = p.yaw
                    if dist > 0.05:
                        mv = float(np.arctan2(d[1], d[0]))
                        if abs(np.angle(np.exp(1j * (mv - p.yaw)))) < np.pi / 2:
                            heading = mv  # walk forward toward the target; otherwise step backward
                    r.true_pose = Pose2D(float(nxt[0]), float(nxt[1]), heading)
                    vx = adv / self.dt
                    if adv >= dist - 1e-9 and self.wp < len(pts) - 1:
                        self.wp += 1
        self.max_speed_seen = max(self.max_speed_seen, vx)
        r.twist = np.array([vx, 0.0, wz])
        return ControlFeedback(r.t, cmd.issued_at, status, msg, blocked_at)


def restaurant(**kw) -> FakeRoom:
    """10x8 m dining room. Tables 1–3 (numbered placards readable within 2 m), a partition
    wall, and a service counter. Robot starts bottom-left facing +x."""
    return FakeRoom([
        Box(1, "counter", np.array([0.2, 6.6, 0.0]), np.array([2.5, 7.6, 1.0])),
        Box(2, "wall", np.array([4.0, 0.0, 0.0]), np.array([4.2, 4.5, 2.0])),
        Box(11, "table", np.array([6.0, 1.0, 0.0]), np.array([7.0, 1.8, 0.75]), {"table_number": "1"}),
        Box(12, "table", np.array([6.0, 5.6, 0.0]), np.array([7.0, 6.4, 0.75]), {"table_number": "2"}),
        Box(13, "table", np.array([8.4, 3.2, 0.0]), np.array([9.4, 4.0, 0.75]), {"table_number": "3"}),
    ], **kw)


def run(executive, room: FakeRoom, controller: KinematicController | None = None, max_s: float = 400.0, hooks=None):
    """Closed loop. `hooks(t, room, executive)` may mutate the world mid-episode."""
    ctrl = controller or KinematicController(room)
    fb = None
    cmds = []
    while room.t < max_s:
        if hooks:
            hooks(room.t, room, executive)
        obs = room.observe()
        cmd = executive.step(obs, fb)
        if not cmds or cmds[-1].issued_at != cmd.issued_at:
            cmds.append(cmd)
        if cmd.kind == CommandKind.STOP:
            return cmd, cmds, ctrl
        fb = ctrl.step(cmd)
    raise AssertionError(f"no terminal command by t={room.t}; state={executive.state} events={executive.events[-10:]}")
