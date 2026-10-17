"""Viewpoint selection for search, and reachable standoff poses for approach.

Navigation owns *feasibility*: every returned goal has a planned collision-free path on
the inflated grid (body + tray clearance). The executive owns *what* to look for.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from autonomy.contracts import OccupancyGrid, Pose2D, Region
from .coverage import CoverageMap
from .planner import inflate, path_length, plan_path


@dataclass
class NavGoal:
    pose: Pose2D
    path: list[tuple[float, float]]
    score: float = 0.0


class Navigator:
    def __init__(self, grid: OccupancyGrid, robot_radius: float = 0.3, view_range: float = 3.5, seed: int = 0):
        self.grid = grid
        self.robot_radius = robot_radius
        self.view_range = view_range
        self.rng = np.random.default_rng(seed)
        self.coverage = CoverageMap(grid, max_range=view_range)
        self.blocked = np.zeros(grid.data.shape, bool)  # contact-reported obstacles (persist)
        self.dynamic = np.zeros(grid.data.shape, bool)  # live depth layer (replaced every update)
        self._visited: list[np.ndarray] = []
        self._refresh()

    def _refresh(self) -> None:
        g = OccupancyGrid(np.where(self.blocked | self.dynamic, OccupancyGrid.OCCUPIED, self.grid.data).astype(np.uint8),
                          self.grid.resolution, self.grid.origin)
        self.free = inflate(g, self.robot_radius)

    # ------------------------------------------------------------------ obstacles
    def mark_blocked(self, xy, radius: float = 0.25) -> None:
        r = int(np.ceil(radius / self.grid.resolution))
        rc = self.grid.world_to_cell(xy)
        H, W = self.blocked.shape
        self.blocked[max(0, rc[0] - r):min(H, rc[0] + r + 1), max(0, rc[1] - r):min(W, rc[1] + r + 1)] = True
        self._refresh()

    def set_dynamic_obstacles(self, mask: np.ndarray) -> bool:
        """Replace the live (depth-derived) obstacle layer. Returns True if the map changed."""
        mask = np.asarray(mask, bool)
        if mask.shape != self.dynamic.shape:
            raise ValueError("dynamic obstacle mask must match the grid")
        if np.array_equal(mask, self.dynamic):
            return False
        self.dynamic = mask.copy()
        self._refresh()
        return True

    def path_is_free(self, path, robot_xy, skip_m: float | None = None) -> bool:
        """True if the part of `path` ahead of the robot only crosses free (inflated) cells.
        The first `skip_m` (default robot radius + 1 cell) is ignored: the robot may stand inside
        an inflated margin, and that must not trigger endless replanning."""
        if not path:
            return True
        skip = self.robot_radius + self.grid.resolution if skip_m is None else skip_m
        pts = [np.asarray(robot_xy, float)] + [np.asarray(q, float) for q in path]
        # start from the closest path vertex ahead of the robot
        dists = [np.linalg.norm(q - pts[0]) for q in pts[1:]]
        k = int(np.argmin(dists))
        seq = [pts[0]] + pts[1 + k:]
        travelled = 0.0
        step = self.grid.resolution * 0.5
        for a, b in zip(seq, seq[1:]):
            seg = float(np.linalg.norm(b - a))
            for t in np.arange(0.0, seg + 1e-9, step):
                if travelled + t < skip:
                    continue
                rc = self.grid.world_to_cell(a + (b - a) * (t / max(seg, 1e-9)))
                if not self.grid.in_bounds(rc) or not self.free[rc]:
                    return False
            travelled += seg
        return True

    def plan(self, start_xy, goal_xy) -> list[tuple[float, float]] | None:
        return plan_path(self.grid, start_xy, goal_xy, free=self.free)

    # ------------------------------------------------------------------ approach
    def approach(self, target_xy, robot: Pose2D, standoff: float) -> NavGoal | None:
        """Reachable pose ~standoff from target, facing it; prefers the robot's side."""
        t = np.asarray(target_xy, float)[:2]
        base = np.arctan2(robot.y - t[1], robot.x - t[0])
        best = None
        for da in np.deg2rad([0, 30, -30, 60, -60, 90, -90, 135, -135, 180]):
            for r in (standoff, standoff * 1.25, standoff * 1.5):
                xy = t + r * np.array([np.cos(base + da), np.sin(base + da)])
                rc = self.grid.world_to_cell(xy)
                if not self.grid.in_bounds(rc) or not self.free[rc]:
                    continue
                path = self.plan(robot.xy(), xy)
                if path is None:
                    continue
                cost = path_length(path) + 0.3 * abs(da) + 3.0 * (r - standoff)
                if best is None or -cost > best.score:
                    yaw = float(np.arctan2(t[1] - xy[1], t[0] - xy[0]))
                    best = NavGoal(Pose2D(float(xy[0]), float(xy[1]), yaw), path, -cost)
        return best

    # ------------------------------------------------------------------ explore
    def mark_visited(self, robot: Pose2D) -> None:
        self._visited.append(robot.xy())

    def unseen_fraction(self) -> float:
        return 1.0 - self.coverage.coverage_fraction(self.free)

    def explore(self, robot: Pose2D, regions: list[Region] = (), hint: str | None = None,
                n_candidates: int = 150) -> NavGoal | None:
        """Best viewpoint by prior-weighted unseen area / travel cost. `hint` boosts regions whose
        name or tags match (e.g. instruction says 'by the window')."""
        unseen = self.free & ~self.coverage.seen
        if not unseen.any():
            return None
        weights = self._prior(regions, hint)
        rr, cc = np.nonzero(self.free)
        idx = self.rng.choice(len(rr), size=min(n_candidates, len(rr)), replace=False)
        best = None
        for i in idx:
            xy = self.grid.cell_to_world((rr[i], cc[i]))
            gain, yaw = self._view_gain(xy, unseen, weights)
            if gain <= 1e-6:
                continue
            path = self.plan(robot.xy(), xy)
            if path is None:
                continue
            revisits = sum(np.linalg.norm(xy - v) < 0.5 for v in self._visited)
            score = gain / (1.0 + 0.5 * path_length(path)) / (1 + revisits)
            if best is None or score > best.score:
                best = NavGoal(Pose2D(float(xy[0]), float(xy[1]), yaw), path, score)
        return best

    def _prior(self, regions, hint) -> np.ndarray:
        w = np.ones(self.grid.data.shape)
        H, W = w.shape
        ys = self.grid.origin[1] + (np.arange(H) + 0.5) * self.grid.resolution
        xs = self.grid.origin[0] + (np.arange(W) + 0.5) * self.grid.resolution
        X, Y = np.meshgrid(xs, ys)
        for reg in regions:
            k = 1.0
            if hint and (hint == reg.name or hint in reg.tags):
                k = 6.0
            d2 = (X - reg.center[0]) ** 2 + (Y - reg.center[1]) ** 2
            w += k * np.exp(-d2 / (2 * max(reg.radius, 0.3) ** 2))
        return w

    def _view_gain(self, xy, unseen, weights, n_dirs: int = 8) -> tuple[float, float]:
        g = self.grid
        r = int(self.view_range / g.resolution)
        rc = g.world_to_cell(xy)
        r0, r1 = max(0, rc[0] - r), min(g.data.shape[0], rc[0] + r + 1)
        c0, c1 = max(0, rc[1] - r), min(g.data.shape[1], rc[1] + r + 1)
        rr, cc = np.nonzero(unseen[r0:r1, c0:c1])
        if len(rr) == 0:
            return 0.0, 0.0
        dy, dx = (rr + r0 - rc[0]) * g.resolution, (cc + c0 - rc[1]) * g.resolution
        dist = np.hypot(dx, dy)
        ok = (dist <= self.view_range) & (dist > 0.3)
        ang = np.arctan2(dy[ok], dx[ok])
        wv = weights[rr[ok] + r0, cc[ok] + c0]
        best = (0.0, 0.0)
        for yaw in np.linspace(-np.pi, np.pi, n_dirs, endpoint=False):
            gain = float(wv[np.abs(np.angle(np.exp(1j * (ang - yaw)))) <= np.pi / 4].sum()) * g.resolution**2
            if gain > best[0]:
                best = (gain, float(yaw))
        return best
