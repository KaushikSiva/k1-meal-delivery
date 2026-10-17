"""One-call autonomy for a velocity-commanded walking loop (e.g. Codex's k1_walk runner at 50 Hz).

    session = AutonomySession(task, grid, detector, regions, deployable=False)
    while running:                                   # control rate, e.g. 50 Hz
        obs = adapter.observe(data) if camera_tick else None   # camera may be slower
        vx, vy, wz = session.tick(obs, now=sim_time, dt=0.02)
        controller.vel_command.{lin_vel_x, lin_vel_y, ang_vel_yaw} = vx, vy, wz
        if session.done: break                       # session.outcome, session.events

- The executive runs on every new camera observation (or feedback); the follower runs every tick
  on the latest pose estimate.
- Ticks between frames are not sensor failures. Once the last frame is older than
  `sensor_stale_s`, the executive runs on the independent clock every `exec_period_s` so sensor
  timeouts still advance.
- Feedback (REACHED) is derived from the pose, so no control feedback is required; pass
  `feedback=` (ControlFeedback) if the controller reports BLOCKED/FAILED.
- Terminal: after STOP the follower ramps to zero and stays there.
No network calls: safe inside the control loop (Codex Q4 decision).
"""

from __future__ import annotations

import numpy as np

from navigation.follower import FollowerLimits, PathFollower
from .contracts import AutonomyCommand, CommandKind, ControlFeedback, Observation, Pose2D
from .executive import DeliveryExecutive, State


class AutonomySession:
    def __init__(self, *args, exec_period_s: float = 0.2, limits: FollowerLimits | None = None, **kwargs):
        self.executive = DeliveryExecutive(*args, **kwargs)
        self.follower = PathFollower(limits)
        self.exec_period_s = exec_period_s
        self.cmd: AutonomyCommand | None = None
        self.pose: Pose2D | None = None
        self._last_exec_t: float | None = None
        self._last_obs_t: float | None = None
        self.history: list[tuple[float, float, float, float, str]] = []  # t, vx, vy, wz, state

    @property
    def done(self) -> bool:
        return self.executive.state in (State.DONE, State.FAILED) and not np.any(np.abs(self.follower.v) > 1e-6)

    @property
    def outcome(self):
        return self.executive.outcome

    @property
    def events(self):
        return self.executive.events

    def tick(self, obs: Observation | None, now: float, dt: float, feedback: ControlFeedback | None = None):
        if obs is not None and obs.pose is not None:
            self.pose = obs.pose.pose
        if obs is not None:
            self._last_obs_t = now
        # Run the executive on every new frame or feedback. Without a frame, only run it once the
        # last frame is actually stale, so sensor timeouts advance; a tick that merely falls
        # between camera frames is NOT a sensor failure.
        stale = self._last_obs_t is None or now - self._last_obs_t > self.executive.cfg.sensor_stale_s
        due = self._last_exec_t is None or now - self._last_exec_t >= self.exec_period_s - 1e-9
        if obs is not None or feedback is not None or (stale and due):
            self.cmd = self.executive.step(obs, feedback, now=now)
            self._last_exec_t = now
        if self.pose is None or self.cmd is None or self.cmd.kind == CommandKind.STOP:
            v = self.follower.step(None, self.pose or Pose2D(0, 0, 0), now, dt)  # ramp down
        else:
            v = self.follower.step(self.cmd, self.pose, now, dt)
        self.history.append((now, float(v[0]), float(v[1]), float(v[2]), self.executive.state.value))
        return float(v[0]), float(v[1]), float(v[2])
