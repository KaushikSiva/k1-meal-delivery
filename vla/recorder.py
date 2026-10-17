"""Demonstration recorder: executive-driven episodes -> VLA training rows.

Teacher labels come from the executive's commands converted into the bounded action space
(`label_from_command`). Rows carry provenance so privileged-sim runs can't silently become
deployment data. Output: JSONL (one row per step) + an .npz of state/action arrays; images
are referenced by path (writing video is left to the sim recorder, Codex-owned).
Converting to LeRobotDataset v3 is a later step once lerobot is pinned.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from autonomy.contracts import AutonomyCommand, CommandKind, Observation, Provenance
from .action_space import DX_MAX, DX_MIN, DY_MAX, DYAW_MAX, LocalSubgoal, encode
from .inputs import build_state, memory_text, to_base


def label_from_command(cmd: AutonomyCommand, obs: Observation, lookahead_m: float = 1.0) -> np.ndarray:
    """Executive command -> normalized 5-d action (the subgoal a VLA should have proposed)."""
    if cmd.kind in (CommandKind.HOLD, CommandKind.STOP) or obs.pose is None:
        return encode(LocalSubgoal(0, 0, 0, 0, True))
    pose = obs.pose.pose
    if cmd.kind == CommandKind.SCAN:
        return encode(LocalSubgoal(0.0, 0.0, float(np.clip(cmd.scan_yaw, -DYAW_MAX, DYAW_MAX)), 0.0, False))
    pts = [np.asarray(q, float) for q in (list(cmd.path or []) + [tuple(cmd.goal_pose.xy())])]
    # Project the robot onto the path, then take a carrot `lookahead_m` further along it.
    best_i, best_p, best_d = 0, pts[0], np.inf
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ab = b - a
        u = float(np.clip(np.dot(pose.xy() - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1))
        q = a + u * ab
        d = np.linalg.norm(q - pose.xy())
        if d < best_d:
            best_i, best_p, best_d = i, q, d
    target, acc, prev = pts[-1], 0.0, best_p
    for q in pts[best_i + 1:]:
        q = np.asarray(q, float)
        seg = np.linalg.norm(q - prev)
        if acc + seg >= lookahead_m:
            target = prev + (q - prev) * (lookahead_m - acc) / max(seg, 1e-9)
            break
        acc, prev = acc + seg, q
    rel = to_base(pose, target)
    final = bool(np.allclose(target, pts[-1]))
    dyaw = float(np.angle(np.exp(1j * (cmd.goal_pose.yaw - pose.yaw)))) if final else float(np.arctan2(rel[1], rel[0]))
    return encode(LocalSubgoal(float(np.clip(rel[0], DX_MIN, DX_MAX)), float(np.clip(rel[1], -DY_MAX, DY_MAX)),
                               float(np.clip(dyaw, -DYAW_MAX, DYAW_MAX)), cmd.max_speed, False))


@dataclass
class DemoRecorder:
    episode_id: str
    provenance: dict  # e.g. {"source": "fixture"|"mujoco"|"isaac", "detector": ..., "privileged_inputs": [...]}
    rows: list[dict] = field(default_factory=list)

    def record(self, obs: Observation, executive, cmd: AutonomyCommand, image_ref: str | None = None) -> None:
        self.rows.append({
            "episode_id": self.episode_id, "frame_index": len(self.rows), "timestamp": obs.timestamp,
            "task": executive.task.instruction, "memory_text": memory_text(executive),
            "executive_state": executive.state.value, "command_kind": cmd.kind.value, "selected_by": cmd.selected_by,
            "observation.state": build_state(obs, executive).tolist(),
            "action": label_from_command(cmd, obs).tolist(), "image_ref": image_ref,
            # Taint rule: memory-derived features (state, memory_text) are privileged if any memory
            # track or the pose was derived from privileged inputs.
            "privileged_features": bool(
                (obs.pose is not None and obs.pose.provenance == Provenance.SIM_PRIVILEGED)
                or any(Provenance.SIM_PRIVILEGED in o.provenance for o in executive.memory.objects.values())),
        })

    def finish(self, out_dir: Path, outcome: str) -> Path:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        meta = {"episode_id": self.episode_id, "outcome": outcome, "n_frames": len(self.rows),
                "privileged_feature_frames": sum(r["privileged_features"] for r in self.rows),
                "provenance": self.provenance, "action_names": ["dx", "dy", "dyaw", "speed", "hold"]}
        (out_dir / f"{self.episode_id}.meta.json").write_text(json.dumps(meta, indent=2))
        with open(out_dir / f"{self.episode_id}.jsonl", "w") as f:
            for r in self.rows:
                f.write(json.dumps(r) + "\n")
        np.savez(out_dir / f"{self.episode_id}.npz",
                 state=np.array([r["observation.state"] for r in self.rows], np.float32),
                 action=np.array([r["action"] for r in self.rows], np.float32))
        return out_dir
