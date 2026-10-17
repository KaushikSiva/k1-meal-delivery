"""AutonomyCommand + estimated pose -> bounded base velocity command (vx, vy, wz).

Bridges the executive to a velocity-commanded walking policy (e.g. Booster's k1_walk
locomotion policy, whose actor takes a velocity command). Runs at the control-command rate
on the robot (no network). Properties:
- Acceleration-limited (NOT jerk-limited) speed profile, stopping distance respected
  (decelerate to zero at the goal: sqrt(2·a·d)), lower accel in FINAL_APPROACH for tray stability.
- Speed cap: the *planar norm* |(vx, vy)| of the target velocity never exceeds
  min(cmd.max_speed, limits) — forward, reverse and lateral alike. max_speed = 0 means rotate only.
- Acceleration: the planar velocity moves straight toward the (capped) target with
  |Δv| ≤ accel·dt per step (vector norm, not per axis). If the current velocity is within the
  cap, it stays within it, including during direction changes.
- Cap reduction semantics: the output converges toward the new bounded target at that
  acceleration bound, with no velocity step. No tighter time bound is claimed for targets that
  keep changing.
- HOLD/STOP/expired command -> decelerate to zero at the same accel limit (never a step to 0).
- SCAN: a relative yaw is converted once (per command) into an absolute target heading, tracked
  with a P-controller, and the rotation stops when reached.
- Pure-pursuit heading on the path; lateral velocity used only for small corrections.
Limits are placeholders until measured with the loaded K1 (unverified).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from autonomy.contracts import AutonomyCommand, CommandKind, Pose2D


@dataclass
class FollowerLimits:
    v_max: float = 0.35  # m/s forward
    v_back: float = 0.1  # m/s backward
    vy_max: float = 0.1  # m/s lateral
    wz_max: float = 0.6  # rad/s
    accel: float = 0.25  # m/s^2 (tray: gentle)
    final_accel: float = 0.15  # m/s^2 in FINAL_APPROACH
    w_accel: float = 1.0  # rad/s^2
    lookahead: float = 0.5  # m
    turn_in_place_rad: float = 0.8  # rotate before walking if heading error is larger
    # Opt-in deadband compensation for walking policies that don't move at small commands
    # (Codex's unloaded k1_walk sweep: ~0.03 m/s achieved at 0.2 m/s commanded). 0 = off (default).
    # When > 0, a nonzero planar target is raised to at least this speed, but NEVER above the
    # command's max_speed; within `stop_radius` of the goal the planar target is exactly 0.
    min_walk_cmd: float = 0.0
    stop_radius: float = 0.05


class PathFollower:
    def __init__(self, limits: FollowerLimits | None = None):
        self.lim = limits or FollowerLimits()
        self.v = np.zeros(3)  # last commanded (vx, vy, wz), base frame
        self._scan_key: float | None = None
        self._scan_target_yaw = 0.0

    def reset(self) -> None:
        self.v[:] = 0
        self._scan_key = None  # a new episode may reuse issued_at values

    def step(self, cmd: AutonomyCommand | None, pose: Pose2D, now: float, dt: float) -> np.ndarray:
        L = self.lim
        target = np.zeros(3)
        accel = L.final_accel if (cmd is not None and cmd.kind == CommandKind.FINAL_APPROACH) else L.accel
        if cmd is not None and now <= cmd.expires_at:
            if cmd.kind == CommandKind.SCAN:
                if self._scan_key != cmd.issued_at:
                    self._scan_key, self._scan_target_yaw = cmd.issued_at, pose.yaw + cmd.scan_yaw
                e = _wrap(self._scan_target_yaw - pose.yaw)
                target[2] = 0.0 if abs(e) < 0.02 else np.clip(1.5 * e, -L.wz_max, L.wz_max)
            elif cmd.kind in (CommandKind.NAVIGATE, CommandKind.FINAL_APPROACH) and cmd.goal_pose is not None:
                target = self._track(cmd, pose, accel)
                cap = max(0.0, min(cmd.max_speed, L.v_max))
                n = float(np.hypot(target[0], target[1]))
                if L.min_walk_cmd > 0 and 1e-6 < n < L.min_walk_cmd:
                    target[:2] *= min(L.min_walk_cmd, cap) / n  # deadband compensation (opt-in)
                    n = float(np.hypot(target[0], target[1]))
                if n > cap:
                    target[:2] *= cap / n
        # Rate-limit toward target (decelerating to zero for HOLD/STOP/expired). The planar step is
        # limited by its *vector norm*, so v moves along the straight segment to the target: if both
        # endpoints are inside the speed ball, every intermediate velocity is too (convexity).
        dv = target[:2] - self.v[:2]
        n = float(np.linalg.norm(dv))
        if n > accel * dt:
            dv *= accel * dt / n
        dw = np.clip(target[2] - self.v[2], -L.w_accel * dt, L.w_accel * dt)
        self.v = np.array([self.v[0] + dv[0], self.v[1] + dv[1], self.v[2] + dw])
        return self.v.copy()

    def _track(self, cmd: AutonomyCommand, pose: Pose2D, accel: float) -> np.ndarray:
        L = self.lim
        pts = [np.asarray(p, float) for p in (cmd.path or ())] + [cmd.goal_pose.xy()]
        remaining, carrot = _carrot(pts, pose.xy(), L.lookahead)
        vmax = min(cmd.max_speed, L.v_max)
        if remaining < max(0.03, L.stop_radius if L.min_walk_cmd > 0 else 0.03):  # at goal: align yaw only
            e = _wrap(cmd.goal_pose.yaw - pose.yaw)
            return np.array([0.0, 0.0, np.clip(1.5 * e, -L.wz_max, L.wz_max)])
        rel = _to_base(pose, carrot)
        heading_err = float(np.arctan2(rel[1], rel[0]))
        v_stop = np.sqrt(2 * accel * remaining)  # can still stop at the goal
        if abs(heading_err) > L.turn_in_place_rad and remaining > 0.3:
            return np.array([0.0, 0.0, np.sign(heading_err) * L.wz_max])
        vx = min(vmax, v_stop) * max(np.cos(heading_err), 0.0)
        if remaining <= 0.3 and rel[0] < 0:  # small overshoot: step back slowly
            vx = -min(L.v_back, v_stop)
        vy = np.clip(rel[1] * 0.5, -L.vy_max, L.vy_max) if remaining < 0.6 else 0.0
        wz = np.clip(1.5 * heading_err, -L.wz_max, L.wz_max) if remaining > 0.3 else \
            np.clip(1.5 * _wrap(cmd.goal_pose.yaw - pose.yaw), -L.wz_max, L.wz_max)
        return np.array([vx, vy, wz])


def _wrap(a):
    return float(np.angle(np.exp(1j * a)))


def _to_base(pose: Pose2D, xy) -> np.ndarray:
    d = np.asarray(xy, float) - pose.xy()
    c, s = np.cos(pose.yaw), np.sin(pose.yaw)
    return np.array([c * d[0] + s * d[1], -s * d[0] + c * d[1]])


def _carrot(pts, p, lookahead):
    """(remaining path length from projection of p, carrot point lookahead ahead)."""
    if len(pts) == 1:
        return float(np.linalg.norm(pts[0] - p)), pts[0]
    best_i, best_q, best_d = 0, pts[0], np.inf
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ab = b - a
        u = float(np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1))
        q = a + u * ab
        d = float(np.linalg.norm(q - p))
        if d < best_d:
            best_i, best_q, best_d = i, q, d
    rem = float(np.linalg.norm(pts[best_i + 1] - best_q)) + sum(
        float(np.linalg.norm(pts[j + 1] - pts[j])) for j in range(best_i + 1, len(pts) - 1))
    rem = max(rem, float(np.linalg.norm(pts[-1] - p)) if best_i == len(pts) - 2 else rem)
    carrot, acc, prev = pts[-1], 0.0, best_q
    for q in pts[best_i + 1:]:
        seg = float(np.linalg.norm(q - prev))
        if acc + seg >= lookahead:
            carrot = prev + (q - prev) * (lookahead - acc) / max(seg, 1e-9)
            break
        acc, prev = acc + seg, q
    return rem, carrot
