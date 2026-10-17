"""Camera geometry helpers (OpenCV convention, see k1_meal.interfaces)."""

from __future__ import annotations

import numpy as np

from autonomy.contracts import CameraIntrinsics


def valid_depth(depth: np.ndarray, max_range: float = np.inf) -> np.ndarray:
    return np.isfinite(depth) & (depth > 1e-6) & (depth <= max_range)


def backproject(
    us: np.ndarray, vs: np.ndarray, zs: np.ndarray, K: CameraIntrinsics, T_world_camera: np.ndarray
) -> np.ndarray:
    """Pixels (u, v) with z-depth -> (N, 3) world points."""
    x = (us - K.cx) * zs / K.fx
    y = (vs - K.cy) * zs / K.fy
    pts_cam = np.stack([x, y, zs, np.ones_like(zs)], axis=-1)
    return (pts_cam @ T_world_camera.T)[:, :3]


def project_points(
    pts_world: np.ndarray, K: CameraIntrinsics, T_world_camera: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(N,3) world points -> (u, v, z_cam). Points behind the camera get z <= 0."""
    pts = np.atleast_2d(pts_world)
    T_cam_world = np.linalg.inv(T_world_camera)
    pc = np.c_[pts, np.ones(len(pts))] @ T_cam_world.T
    z = pc[:, 2]
    safe_z = np.where(np.abs(z) < 1e-9, 1e-9, z)
    u = K.fx * pc[:, 0] / safe_z + K.cx
    v = K.fy * pc[:, 1] / safe_z + K.cy
    return u, v, z


def visible_mask(
    pts_world: np.ndarray,
    K: CameraIntrinsics,
    T_world_camera: np.ndarray,
    depth: np.ndarray | None = None,
    max_range: float = 6.0,
    occlusion_tol: float = 0.15,
    margin_px: int = 4,
) -> np.ndarray:
    """Which world points *should* be seen in this frame (in frustum, in range, not occluded).

    Used by memory for negative evidence: an object that should be visible but isn't
    detected loses confidence.
    """
    u, v, z = project_points(pts_world, K, T_world_camera)
    ok = (
        (z > 0.05)
        & (z <= max_range)
        & (u >= margin_px)
        & (u < K.width - margin_px)
        & (v >= margin_px)
        & (v < K.height - margin_px)
    )
    if depth is not None and ok.any():
        ui = np.clip(u[ok].astype(int), 0, K.width - 1)
        vi = np.clip(v[ok].astype(int), 0, K.height - 1)
        d = depth[vi, ui]
        # Occluded if something valid is clearly in front of the point.
        occluded = valid_depth(d) & (d < z[ok] - occlusion_tol)
        idx = np.flatnonzero(ok)
        ok[idx[occluded]] = False
    return ok
