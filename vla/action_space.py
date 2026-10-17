"""Bounded VLA action space for K1 delivery (PROPOSAL, see docs/autonomy/VLA_DATA_SPEC.md).

The VLA does NOT output joint targets. It proposes a short-horizon *local subgoal* in the
robot base frame; the BoundedActionAdapter checks it and turns it into an AutonomyCommand
for navigation + the carrying controller (which owns balance and joints).

Normalized action vector a in [-1, 1]^5 (one row of a SmolVLA-style chunk):
    0  dx     forward subgoal offset      -> [DX_MIN, DX_MAX] m (base frame)
    1  dy     lateral subgoal offset      -> [-DY_MAX, DY_MAX] m
    2  dyaw   heading change at subgoal   -> [-DYAW_MAX, DYAW_MAX] rad
    3  speed  speed fraction              -> [0, V_MAX] m/s
    4  hold   >= 0 means "stop and observe" (HOLD); the VLA cannot declare delivery
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DX_MIN, DX_MAX = -0.3, 1.5
DY_MAX = 0.8
DYAW_MAX = np.pi / 2
V_MAX = 0.35  # below the ~0.4 m/s K1 walking figure in Booster marketing (unverified, loaded tray)
ACTION_DIM = 5
ACTION_NAMES = ("dx", "dy", "dyaw", "speed", "hold")


@dataclass(frozen=True)
class LocalSubgoal:
    dx: float
    dy: float
    dyaw: float
    speed: float
    hold: bool


def _lin(a, lo, hi):
    return lo + (np.clip(a, -1, 1) + 1) * 0.5 * (hi - lo)


def _inv(x, lo, hi):
    return float(np.clip(2 * (x - lo) / (hi - lo) - 1, -1, 1))


def decode(a: np.ndarray) -> LocalSubgoal:
    a = np.asarray(a, float).reshape(-1)
    if a.shape[0] != ACTION_DIM:
        raise ValueError(f"expected {ACTION_DIM}-dim action, got {a.shape}")
    if not np.all(np.isfinite(a)):
        raise ValueError("non-finite action")
    return LocalSubgoal(
        dx=float(_lin(a[0], DX_MIN, DX_MAX)), dy=float(_lin(a[1], -DY_MAX, DY_MAX)),
        dyaw=float(_lin(a[2], -DYAW_MAX, DYAW_MAX)), speed=float(_lin(a[3], 0.0, V_MAX)), hold=bool(a[4] >= 0),
    )


def encode(g: LocalSubgoal) -> np.ndarray:
    return np.array([
        _inv(g.dx, DX_MIN, DX_MAX), _inv(g.dy, -DY_MAX, DY_MAX), _inv(g.dyaw, -DYAW_MAX, DYAW_MAX),
        _inv(g.speed, 0.0, V_MAX), 1.0 if g.hold else -1.0,
    ], dtype=np.float32)
