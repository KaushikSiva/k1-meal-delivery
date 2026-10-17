"""BoundedActionAdapter: VLA proposal -> safe AutonomyCommand, or executive fallback.

The executive remains the authority for safety states and task completion:
- In RELOCALIZE / SENSOR_WAIT / SETTLE / DONE / FAILED the executive command always wins.
- Proposals that are stale, non-finite, infeasible (no path / occupied) or exceed bounds
  are rejected (non-finite/stale/infeasible) or clipped (bounds), and every decision is logged.
- A VLA "hold" becomes HOLD; the VLA can never emit STOP/DELIVERED.
Selected commands are labeled selected_by="vla" for evaluation attribution.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

import numpy as np

from autonomy.contracts import AutonomyCommand, CommandKind, Observation, Pose2D
from autonomy.executive import DeliveryExecutive, State
from navigation.planner import path_length
from .action_space import decode

EXECUTIVE_ONLY = {State.RELOCALIZE, State.SENSOR_WAIT, State.SETTLE, State.DONE, State.FAILED, State.FINAL_APPROACH}


@dataclass
class VLAProposal:
    actions: np.ndarray  # (T, 5) normalized chunk, or (5,)
    timestamp: float  # observation time the model conditioned on
    model_id: str = "unknown"
    latency_s: float | None = None


@dataclass
class AdapterDecision:
    t: float
    accepted: bool
    reason: str
    model_id: str


@dataclass
class BoundedActionAdapter:
    max_age_s: float = 0.6
    ttl_s: float = 0.8
    max_detour_ratio: float = 2.0
    decisions: list[AdapterDecision] = field(default_factory=list)

    def select(self, executive: DeliveryExecutive, exec_cmd: AutonomyCommand, obs: Observation,
               proposal: VLAProposal | None) -> AutonomyCommand:
        ok, why, cmd = self._try(executive, exec_cmd, obs, proposal)
        self.decisions.append(AdapterDecision(executive.now, ok, why, proposal.model_id if proposal else "none"))
        return cmd if ok else exec_cmd

    def _try(self, ex, exec_cmd, obs, p):
        if p is None:
            return False, "no proposal", None
        if ex.state in EXECUTIVE_ONLY or exec_cmd.kind == CommandKind.STOP:
            return False, f"executive-only state {ex.state.value}", None
        if obs.pose is None or ex.now - p.timestamp > self.max_age_s:
            return False, "stale proposal or no pose", None
        try:
            g = decode(np.atleast_2d(p.actions)[0])
        except ValueError as e:
            return False, f"invalid action: {e}", None
        now = ex.now
        if g.hold:
            return True, "vla hold", AutonomyCommand(CommandKind.HOLD, now, now + self.ttl_s, reason="vla: hold/observe",
                                                     state=ex.state.value, selected_by="vla")
        pose = obs.pose.pose
        c, s = np.cos(pose.yaw), np.sin(pose.yaw)
        gx, gy = pose.x + c * g.dx - s * g.dy, pose.y + s * g.dx + c * g.dy
        rc = ex.nav.grid.world_to_cell((gx, gy))
        if not ex.nav.grid.in_bounds(rc) or not ex.nav.free[rc]:
            return False, "subgoal in occupied/inflated cell", None
        path = ex.nav.plan(pose.xy(), (gx, gy))
        straight = float(np.hypot(gx - pose.x, gy - pose.y))
        if path is None or path_length(path) > self.max_detour_ratio * straight + 0.3:
            return False, "subgoal not reachable locally", None
        speed = min(g.speed, exec_cmd.max_speed if exec_cmd.kind == CommandKind.NAVIGATE else g.speed)
        if ex._degraded:
            speed = min(speed, ex.cfg.degraded_speed)
        return True, "accepted", AutonomyCommand(
            CommandKind.NAVIGATE, now, now + self.ttl_s, goal_pose=Pose2D(gx, gy, pose.yaw + g.dyaw),
            path=tuple(map(tuple, path)), max_speed=speed, reason="vla local subgoal", state=ex.state.value,
            selected_by="vla",
        )
