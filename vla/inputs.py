"""Build VLA model inputs with *explicit* scene memory.

A VLA has no long-term memory or SLAM. We inject the executive's memory two ways:
1. `observation.state` — fixed-layout float vector (below) with the current target
   hypothesis in the base frame, its confidence/age, localization uncertainty, phase.
2. `task` — the instruction plus a short textual memory summary.

STATE_LAYOUT (float32, 16):
  0  has_target           1 if a destination hypothesis exists
  1  target_dx_base (m)   2 target_dy_base (m)   3 target_dist (m)
  4  target_conf [0,1]    5 target_age_s / 60 (clipped to 1)
  6  target_verdict: 1 confirmed, 0.5 possible, 0 none
  7  loc_xy_sigma (m, clipped 1)   8 loc_status: 1 ok, 0.5 degraded, 0 lost
  9  base_vx (m/s)  10 base_vy (m/s)  11 base_wz (rad/s)
  12..15 phase one-hot: search, verify/reacquire, approach/final, hold/other
Privileged values are never used: everything comes from the estimated pose and memory.
"""

from __future__ import annotations

import numpy as np

from autonomy.contracts import LocalizationStatus, Observation
from autonomy.grounding import Verdict, match_candidates

STATE_DIM = 16
_PHASE = {"search": 12, "verify": 13, "reacquire": 13, "approach": 14, "final_approach": 14}


def to_base(pose, xy):
    d = np.asarray(xy[:2], float) - pose.xy()
    c, s = np.cos(-pose.yaw), np.sin(-pose.yaw)
    return np.array([c * d[0] - s * d[1], s * d[0] + c * d[1]])


def build_state(obs: Observation, executive) -> np.ndarray:
    st = np.zeros(STATE_DIM, np.float32)
    pose = obs.pose.pose if obs.pose else None
    cands = [c for c in match_candidates(executive.task.destination, executive.memory) if c.verdict != Verdict.REJECTED]
    tgt = executive._target() if executive.ctx.target_key else (cands[0].obj if cands else None)
    if tgt is not None and pose is not None:
        rel = to_base(pose, tgt.position)
        verdict = next((c.verdict for c in cands if c.obj.key == tgt.key), None)
        st[0:7] = [1, rel[0], rel[1], np.linalg.norm(rel), tgt.confidence, min(tgt.age(executive.now) / 60, 1),
                   1.0 if verdict == Verdict.CONFIRMED else 0.5 if verdict == Verdict.POSSIBLE else 0.0]
    if obs.pose is not None:
        st[7] = min(obs.pose.xy_sigma, 1.0)
        st[8] = {LocalizationStatus.OK: 1.0, LocalizationStatus.DEGRADED: 0.5}.get(obs.pose.status, 0.0)
    if obs.base_twist is not None:
        st[9:12] = obs.base_twist
    st[_PHASE.get(executive.state.value, 15)] = 1
    return st


def memory_text(executive, k: int = 4) -> str:
    pose = executive.last_pose
    parts = []
    for c in match_candidates(executive.task.destination, executive.memory)[:k]:
        o = c.obj
        where = ""
        if pose is not None:
            rel = to_base(pose, o.position)
            where = f" {np.linalg.norm(rel):.1f}m at {np.degrees(np.arctan2(rel[1], rel[0])):+.0f}deg"
        num = o.attribute("table_number")[0]
        parts.append(f"{o.label}{' ' + num if num else ''}:{c.verdict.value}{where}, seen {o.age(executive.now):.0f}s ago")
    return "; ".join(parts) if parts else "no candidates seen yet"


def build_inputs(obs: Observation, executive) -> dict:
    """LeRobot-style feature dict. Image is the head RGB frame (H,W,3 uint8) if present."""
    return {
        "observation.images.head": None if obs.camera is None else obs.camera.rgb,
        "observation.state": build_state(obs, executive),
        "task": f"{executive.task.instruction} | state: {executive.state.value} | memory: {memory_text(executive)}",
        "timestamp": obs.timestamp,
    }
