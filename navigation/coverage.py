"""Tracks which floor cells the camera has already looked at."""

from __future__ import annotations

import numpy as np

from autonomy.contracts import OccupancyGrid, Observation


class CoverageMap:
    def __init__(self, grid: OccupancyGrid, max_range: float = 4.0, n_rays: int = 61):
        self.grid = grid
        self.seen = np.zeros_like(grid.data, dtype=bool)
        self.max_range = max_range
        self.n_rays = n_rays

    def update(self, obs: Observation) -> None:
        cam = obs.T_map_camera()
        if cam is None:
            return
        origin = cam[:3, 3][:2]
        fwd = cam[:3, 2][:2]  # OpenCV z axis = viewing direction
        if np.linalg.norm(fwd) < 1e-6:
            return  # looking straight down/up: no planar coverage
        yaw = float(np.arctan2(fwd[1], fwd[0]))
        self.mark_wedge(origin, yaw, obs.camera.intrinsics.hfov)

    def mark_wedge(self, origin_xy, yaw: float, hfov: float) -> None:
        g = self.grid
        step = g.resolution * 0.5
        n_steps = int(self.max_range / step)
        for a in np.linspace(yaw - hfov / 2, yaw + hfov / 2, self.n_rays):
            d = np.array([np.cos(a), np.sin(a)])
            for k in range(1, n_steps + 1):
                rc = g.world_to_cell(np.asarray(origin_xy) + d * k * step)
                if not g.in_bounds(rc):
                    break
                self.seen[rc] = True
                if g.data[rc] == OccupancyGrid.OCCUPIED:
                    break

    def coverage_fraction(self, free_mask: np.ndarray | None = None) -> float:
        m = self.grid.data != OccupancyGrid.OCCUPIED if free_mask is None else free_mask
        return float(self.seen[m].mean()) if m.any() else 1.0
