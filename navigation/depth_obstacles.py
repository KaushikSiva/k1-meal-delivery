"""Live obstacle layer from depth images (log-odds occupancy on the planning grid).

Each frame (only while localization is OK — a wrong pose would smear obstacles):
- back-project a strided subset of valid depth pixels with the *estimated* camera pose;
- points with height in [z_min, z_max] (body + tray envelope) are obstacle hits;
- cells along the ray from the camera to each hit or floor return are free evidence
  (so moved furniture and people who walked away get cleared);
- log-odds are clamped; cells with probability > p_occ are reported occupied, dilated by
  `dilate_cells` so the inflated planner keeps true clearance despite grid discretization.
The prior floor plan stays separate (labeled operator prior); this layer is ESTIMATED.

Integration: `apply_to(navigator)` -> Navigator.set_dynamic_obstacles(layer.occupied) (public API;
the live layer is replaced each time, so cleared obstacles disappear from planning too).
"""

from __future__ import annotations

import numpy as np

from autonomy.contracts import LocalizationStatus, Observation, OccupancyGrid
from perception.geometry import backproject, valid_depth


class DepthObstacleLayer:
    def __init__(self, grid: OccupancyGrid, z_min: float = 0.08, z_max: float = 1.3, max_range: float = 4.0,
                 stride: int = 3, l_hit: float = 0.85, l_free: float = -0.4, l_clamp: float = 4.0,
                 p_occ: float = 0.7, min_range: float = 0.3, dilate_cells: int = 1):
        self.grid = grid
        self.logodds = np.zeros(grid.data.shape, np.float32)
        self.z_min, self.z_max, self.max_range, self.stride = z_min, z_max, max_range, stride
        self.l_hit, self.l_free, self.l_clamp = l_hit, l_free, l_clamp
        self.l_occ = float(np.log(p_occ / (1 - p_occ)))
        self.min_range = min_range
        self.dilate_cells = dilate_cells  # covers cell discretization + depth noise at the obstacle edge
        self.frames_used = 0
        self.frames_skipped = 0

    def update(self, obs: Observation) -> bool:
        cam = obs.camera
        T = obs.T_map_camera()
        if T is None or cam.depth is None or obs.pose.status != LocalizationStatus.OK:
            self.frames_skipped += 1
            return False
        d = cam.depth[::self.stride, ::self.stride]
        vs, us = np.nonzero(valid_depth(d, self.max_range))
        if len(vs) == 0:
            self.frames_skipped += 1
            return False
        z = d[vs, us].astype(float)
        pts = backproject(us * self.stride + 0.0, vs * self.stride + 0.0, z, cam.intrinsics, T)
        origin = T[:3, 3]
        horiz = np.hypot(pts[:, 0] - origin[0], pts[:, 1] - origin[1])
        keep = horiz >= self.min_range
        pts, horiz = pts[keep], horiz[keep]
        hit = (pts[:, 2] >= self.z_min) & (pts[:, 2] <= self.z_max)
        g = self.grid
        H, W = self.logodds.shape
        res = g.resolution

        def cells(xy):
            c = np.floor((xy[..., 0] - g.origin[0]) / res).astype(np.int64)
            r = np.floor((xy[..., 1] - g.origin[1]) / res).astype(np.int64)
            ok = (r >= 0) & (r < H) & (c >= 0) & (c < W)
            return r, c, ok

        # Free evidence: sample every ray at half-cell steps, stopping one cell short of its end.
        n_steps = int(np.ceil(self.max_range / (res * 0.5)))
        ts = (np.arange(n_steps) + 0.5) * res * 0.5  # metres along the horizontal ray
        d = pts[:, :2] - origin[:2]
        u = d / np.maximum(horiz[:, None], 1e-9)
        samples = origin[:2] + u[:, None, :] * ts[None, :, None]  # (N, S, 2)
        inside = ts[None, :] < (horiz[:, None] - res)
        r, c, ok = cells(samples)
        ok &= inside
        free = np.zeros((H, W), bool)
        free[r[ok], c[ok]] = True
        hr, hc, hok = cells(pts[hit, :2])
        hits = np.zeros((H, W), bool)
        hits[hr[hok], hc[hok]] = True
        free &= ~hits
        self.logodds[free] += self.l_free
        self.logodds[hits] += self.l_hit
        np.clip(self.logodds, -self.l_clamp, self.l_clamp, out=self.logodds)
        self.frames_used += 1
        return True

    @property
    def occupied(self) -> np.ndarray:
        occ = self.logodds > self.l_occ
        out = occ.copy()
        k = self.dilate_cells
        H, W = occ.shape
        for dr in range(-k, k + 1):
            for dc in range(-k, k + 1):
                src = occ[max(0, -dr):H - max(0, dr), max(0, -dc):W - max(0, dc)]
                out[max(0, dr):H - max(0, -dr) if dr < 0 else H, max(0, dc):W - max(0, -dc) if dc < 0 else W] |= src
        return out

    def apply_to(self, navigator) -> bool:
        return navigator.set_dynamic_obstacles(self.occupied)
