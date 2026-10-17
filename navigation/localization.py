"""Deployable 2D localization: command dead-reckoning + depth scan matching to the floor plan.

Inputs (no simulator truth):
  - commanded base velocity (known on the robot) for prediction, with large process noise because
    walking policies track commands poorly (Codex's unloaded k1_walk sweep);
  - depth image + camera extrinsics (calibration/head joints) for correction;
  - the operator floor plan (OccupancyGrid prior).
Output: PoseEstimate(provenance=ESTIMATED, cov from the match-score distribution, status).

Correction = correlative scan matching (Olson-style) with a free-space check (the ray must reach
each hit through free space, which rejects "seeing through" thin walls onto their back faces): depth points in a height band that sees walls
and furniture are projected to the floor, scored against a Gaussian likelihood field of the floor
plan's occupied cells over a (dx, dy, dyaw) window around the prediction; the pose is the best
hypothesis and the covariance is the score-weighted spread of hypotheses. Degenerate geometry
(e.g. a long featureless corridor) therefore yields large covariance along the ambiguous axis, and a
weak match marks the estimate DEGRADED/LOST instead of inventing a pose.

Limits: assumes the map is mostly right and the floor is flat; unmapped objects (people, carts) are
outliers the likelihood field tolerates up to a point; no global relocalization (kidnapping) beyond
the search window; extrinsics must be good (head joints + trunk attitude estimate).
"""

from __future__ import annotations

import numpy as np

from autonomy.contracts import LocalizationStatus, Observation, OccupancyGrid, Pose2D, PoseEstimate, Provenance
from perception.geometry import valid_depth


def distance_field(grid: OccupancyGrid) -> np.ndarray:
    """Approximate Euclidean distance (m) from each cell to the nearest obstacle *surface* cell
    (occupied with a free 4-neighbour). Using surfaces, not filled interiors, matters: a depth scan
    sees surfaces, and a scan shifted *into* a solid block must score badly (with an interior-zero
    field it scores perfectly and the matcher drifts into obstacles)."""
    occ_all = grid.data == OccupancyGrid.OCCUPIED
    free = ~occ_all
    nb_free = np.zeros_like(occ_all)
    nb_free[1:, :] |= free[:-1, :]
    nb_free[:-1, :] |= free[1:, :]
    nb_free[:, 1:] |= free[:, :-1]
    nb_free[:, :-1] |= free[:, 1:]
    occ = occ_all & nb_free
    H, W = occ.shape
    big = 1e9
    d = np.where(occ, 0.0, big)
    a, b = 1.0, np.sqrt(2.0)
    for r in range(H):  # forward pass
        for c in range(W):
            v = d[r, c]
            if v == 0:
                continue
            if r > 0:
                v = min(v, d[r - 1, c] + a)
                if c > 0:
                    v = min(v, d[r - 1, c - 1] + b)
                if c < W - 1:
                    v = min(v, d[r - 1, c + 1] + b)
            if c > 0:
                v = min(v, d[r, c - 1] + a)
            d[r, c] = v
    for r in range(H - 1, -1, -1):  # backward pass
        for c in range(W - 1, -1, -1):
            v = d[r, c]
            if v == 0:
                continue
            if r < H - 1:
                v = min(v, d[r + 1, c] + a)
                if c > 0:
                    v = min(v, d[r + 1, c - 1] + b)
                if c < W - 1:
                    v = min(v, d[r + 1, c + 1] + b)
            if c < W - 1:
                v = min(v, d[r, c + 1] + a)
            d[r, c] = v
    return d * grid.resolution


class ScanMatchLocalizer:
    def __init__(self, grid: OccupancyGrid, initial: Pose2D, initial_sigma=(0.1, 0.1, 0.05),
                 z_band=(0.15, 1.6), max_range: float = 5.0, sigma_hit: float = 0.08, max_points: int = 500,
                 win_xy: float = 0.2, win_yaw: float = 0.12, step_xy: float = 0.025, step_yaw: float = 0.01,
                 slip: float = 0.6, min_inlier_frac: float = 0.35, seed: int = 0,
                 reloc_xy: float = 2.5, reloc_yaw: float = np.pi / 2):
        self.grid = grid
        self.df = distance_field(grid)
        self.pose = np.array([initial.x, initial.y, initial.yaw], float)
        self.cov = np.diag(np.square(initial_sigma)).astype(float)
        self.z_band, self.max_range, self.sigma_hit, self.max_points = z_band, max_range, sigma_hit, max_points
        self.win_xy, self.win_yaw, self.step_xy, self.step_yaw = win_xy, win_yaw, step_xy, step_yaw
        self.slip = slip  # fraction of commanded motion treated as 1-sigma uncertainty
        self.min_inlier_frac = min_inlier_frac
        self.reloc_xy, self.reloc_yaw = reloc_xy, reloc_yaw
        self.last_reloc: dict = {}
        self.status = LocalizationStatus.OK
        self.t = None
        self.rng = np.random.default_rng(seed)
        self.last_match: dict = {}

    # ------------------------------------------------------------------ prediction
    def predict(self, v_cmd, dt: float, scale: float = 1.0) -> None:
        """Dead-reckon with the commanded (vx, vy, wz); `scale` = expected tracking ratio."""
        vx, vy, wz = (float(v) * scale for v in v_cmd)
        x, y, th = self.pose
        c, s = np.cos(th), np.sin(th)
        self.pose = np.array([x + (c * vx - s * vy) * dt, y + (s * vx + c * vy) * dt, th + wz * dt])
        dist = np.hypot(vx, vy) * dt
        q = np.diag([(self.slip * dist) ** 2 + (0.002) ** 2, (self.slip * dist) ** 2 + (0.002) ** 2,
                     (self.slip * abs(wz) * dt) ** 2 + (0.3 * dist) ** 2 + (0.001) ** 2])
        self.cov = self.cov + q

    # ------------------------------------------------------------------ correction
    def _scan_points(self, obs: Observation) -> np.ndarray | None:
        cam = obs.camera
        if cam is None or cam.depth is None:
            return None
        d = cam.depth
        stride = max(1, int(np.sqrt(d.size / (self.max_points * 4))))
        sub = d[::stride, ::stride]
        vs, us = np.nonzero(valid_depth(sub, self.max_range))
        if len(vs) == 0:
            return None
        z = sub[vs, us].astype(float)
        K = cam.intrinsics
        uu, vv = us * float(stride), vs * float(stride)
        pc = np.stack([(uu - K.cx) * z / K.fx, (vv - K.cy) * z / K.fy, z, np.ones_like(z)], -1)
        pb = pc @ cam.T_base_camera.T  # base frame (x fwd, y left, z up)
        keep = (pb[:, 2] >= self.z_band[0]) & (pb[:, 2] <= self.z_band[1])
        pts = pb[keep, :2]
        self._cam_xy = cam.T_base_camera[:2, 3].copy()
        if len(pts) > self.max_points:
            pts = pts[self.rng.choice(len(pts), self.max_points, replace=False)]
        return pts if len(pts) >= 20 else None

    def correct(self, obs: Observation) -> bool:
        pts = self._scan_points(obs)
        if pts is None:
            self._degrade("no usable depth points")
            return False
        x0, y0, th0 = self.pose
        sig_xy = float(np.sqrt(max(self.cov[0, 0], self.cov[1, 1])))
        sig_th = float(np.sqrt(self.cov[2, 2]))
        pre = self._pre_hits(pts)
        occ = self.grid.data == OccupancyGrid.OCCUPIED
        if self.status == LocalizationStatus.LOST or 3 * sig_xy > self.win_xy:
            # Relocalization: coarse-to-fine search over the (bounded) uncertainty region.
            wxy = float(np.clip(3 * sig_xy, self.win_xy, self.reloc_xy))
            wth = float(np.clip(3 * sig_th, self.win_yaw, self.reloc_yaw))
            coarse = self._search(pts, pre, occ, x0, y0, th0, wxy, wth, max(0.1, wxy / 25), max(0.04, wth / 15))
            k = int(np.argmax(coarse[:, 0]))
            x0, y0, th0 = coarse[k, 1:]
            self.last_reloc = {"window_xy": wxy, "window_yaw": wth, "coarse_best": float(coarse[k, 0])}
            wxy, wth = 0.15, 0.08
        else:
            wxy = float(np.clip(3 * sig_xy, self.step_xy * 2, self.win_xy))
            wth = float(np.clip(3 * sig_th, self.step_yaw * 2, self.win_yaw))
        xs = np.arange(-wxy, wxy + 1e-9, self.step_xy)
        ths = np.arange(-wth, wth + 1e-9, self.step_yaw)
        cand = self._search(pts, pre, occ, x0, y0, th0, wxy, wth, self.step_xy, self.step_yaw)
        best = float(cand[:, 0].max())
        # Score-weighted mean/covariance over hypotheses (sharpened); ties are averaged, not picked.
        w = np.exp((cand[:, 0] - best) / 0.02)
        w /= w.sum()
        mean = (w[:, None] * cand[:, 1:]).sum(0)
        diff = cand[:, 1:] - mean
        diff[:, 2] = np.angle(np.exp(1j * diff[:, 2]))
        cov_m = (w[:, None, None] * np.einsum("ni,nj->nij", diff, diff)).sum(0)
        cov_m += np.diag([(self.step_xy / 2) ** 2, (self.step_xy / 2) ** 2, (self.step_yaw / 2) ** 2])
        # Degeneracy: if near-best hypotheses reach the search-window edge along an axis, the scan
        # does not constrain that axis (e.g. sliding along a single wall). Then the window-truncated
        # spread would understate the uncertainty, so declare that axis uninformative instead.
        near = cand[cand[:, 0] >= best - 0.01, 1:]
        unconstrained = []
        for ax, (lo, hi, c0) in enumerate(((xs[0], xs[-1], x0), (xs[0], xs[-1], y0), (ths[0], ths[-1], th0))):
            off = near[:, ax] - c0
            if off.min() <= lo + 1e-9 or off.max() >= hi - 1e-9:
                unconstrained.append(ax)
        # rotate the uncertainty into the ambiguous direction: use eigen-decomposition of the xy block
        if unconstrained:
            for ax in unconstrained:
                cov_m[ax, :] = 0.0
                cov_m[:, ax] = 0.0
                cov_m[ax, ax] = 1e4
        qx, qy = self._rot(pre, mean[2])
        inl = (self._score_xy(*self._rot(pts, mean[2]), mean[0], mean[1]) > 0.6) & \
            ~self._occupied_at(occ, qx, qy, mean[0], mean[1])
        inlier_frac = float(inl.mean())
        self.last_match = {"score": best, "inlier_frac": inlier_frac, "n_points": len(pts),
                           "unconstrained_axes": unconstrained}
        if inlier_frac < self.min_inlier_frac:
            self._degrade(f"weak match (inliers {inlier_frac:.2f})")
            return False
        if len(unconstrained) == 3:
            self._degrade("scan constrains nothing")
            return False
        # Fuse measurement with prediction (information form).
        P_inv, M_inv = np.linalg.inv(self.cov), np.linalg.inv(cov_m)
        cov_new = np.linalg.inv(P_inv + M_inv)
        z = mean.copy()
        z[2] = th0 + np.angle(np.exp(1j * (z[2] - th0)))
        self.pose = cov_new @ (P_inv @ self.pose + M_inv @ z)
        self.cov = 0.5 * (cov_new + cov_new.T)
        sig = float(np.sqrt(np.linalg.eigvalsh(self.cov[:2, :2]).max()))
        self.status = LocalizationStatus.OK if sig <= 0.15 else LocalizationStatus.DEGRADED
        return True

    def _search(self, pts, pre, occ, x0, y0, th0, wxy, wth, sxy, sth) -> np.ndarray:
        """Score all (x, y, yaw) hypotheses in the window -> array of (score, x, y, yaw)."""
        xs = np.arange(-wxy, wxy + 1e-9, sxy)
        ths = np.arange(-wth, wth + 1e-9, sth)
        out = []
        for dth in ths:
            th = th0 + dth
            rx, ry = self._rot(pts, th)
            qx, qy = self._rot(pre, th)
            for dx in xs:
                for dy in xs:
                    # hit must lie on a surface AND the ray must arrive through free space
                    # (rejects "seeing through" a thin wall onto its back face)
                    hit = self._score_xy(rx, ry, x0 + dx, y0 + dy)
                    blocked = self._occupied_at(occ, qx, qy, x0 + dx, y0 + dy)
                    out.append((float((hit * ~blocked).mean()), x0 + dx, y0 + dy, th))
        return np.array(out)

    def _pre_hits(self, pts: np.ndarray, back: float = 0.15) -> np.ndarray:
        """Points `back` metres before each hit along the camera ray (base frame): must be free."""
        d = pts - self._cam_xy
        n = np.linalg.norm(d, axis=1, keepdims=True)
        return pts - d / np.maximum(n, 1e-6) * np.minimum(back, 0.5 * n)

    def _rot(self, pts, th):
        c, s = np.cos(th), np.sin(th)
        return c * pts[:, 0] - s * pts[:, 1], s * pts[:, 0] + c * pts[:, 1]

    def _occupied_at(self, occ, rx, ry, x, y):
        g = self.grid
        col = np.floor((x + rx - g.origin[0]) / g.resolution).astype(int)
        row = np.floor((y + ry - g.origin[1]) / g.resolution).astype(int)
        H, W = occ.shape
        inside = (row >= 0) & (row < H) & (col >= 0) & (col < W)
        out = np.zeros(len(rx), bool)
        out[inside] = occ[row[inside], col[inside]]
        return out

    def _score_xy(self, rx, ry, x, y):
        g = self.grid
        col = np.floor((x + rx - g.origin[0]) / g.resolution).astype(int)
        row = np.floor((y + ry - g.origin[1]) / g.resolution).astype(int)
        H, W = self.df.shape
        inside = (row >= 0) & (row < H) & (col >= 0) & (col < W)
        dist = np.full(len(rx), 1.0)
        dist[inside] = self.df[row[inside], col[inside]]
        return np.exp(-0.5 * (dist / self.sigma_hit) ** 2)

    def _degrade(self, why: str) -> None:
        sig = float(np.sqrt(np.linalg.eigvalsh(self.cov[:2, :2]).max()))
        self.status = LocalizationStatus.LOST if sig > 0.4 else LocalizationStatus.DEGRADED
        self.last_match = {"reason": why}

    # ------------------------------------------------------------------ output
    def estimate(self, t: float) -> PoseEstimate:
        return PoseEstimate(Pose2D(*map(float, self.pose)), self.cov.copy(), t, "cmd_odom+scan_match",
                            Provenance.ESTIMATED, self.status)
