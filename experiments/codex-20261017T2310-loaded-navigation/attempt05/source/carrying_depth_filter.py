"""Invalidate measured depth inside an explicitly configured carried-load envelope.

Uses head encoders and the calibrated camera chain only. This is a geometric
self-filter for the declared carrying posture, not object recognition. It cannot
recover background behind the load or detect a dropped tray. Raw frames should
be retained for audit. Bounds must be calibrated before hardware use.
"""
from dataclasses import replace
import numpy as np
from perception.k1_camera import T_trunk_camera

DEFAULT_BOUNDS = np.array([[.08,-.30,.02],[.55,.30,.34]])


def mask_depth_in_volume(depth, intrinsics, T_trunk_optical, bounds=DEFAULT_BOUNDS):
    bounds=np.asarray(bounds,float);T=np.asarray(T_trunk_optical,float)
    if bounds.shape!=(2,3) or not np.isfinite(bounds).all() or not (bounds[1]>bounds[0]).all():
        raise ValueError('Expected finite, ordered 3D carrying bounds')
    if T.shape!=(4,4) or not np.isfinite(T).all():raise ValueError('Invalid camera transform')
    depth=np.asarray(depth)
    if depth.ndim!=2:raise ValueError('Depth must be an HxW array')
    v,u=np.indices(depth.shape)
    z=depth.astype(float)
    points=np.stack(((u-intrinsics.cx)*z/intrinsics.fx,
                     (v-intrinsics.cy)*z/intrinsics.fy,z),axis=-1)
    points=points@T[:3,:3].T+T[:3,3]
    mask=np.isfinite(z)&(z>0)&np.all((points>=bounds[0])&(points<=bounds[1]),axis=-1)
    filtered=depth.astype(np.float32,copy=True);filtered[mask]=np.nan
    return filtered,mask


def filter_known_carrying_volume(frame, telemetry):
    if abs(frame.timestamp-telemetry.timestamp)>1e-6:raise ValueError('Unsynchronized camera/encoders')
    encoders=dict(zip(telemetry.joint_names,telemetry.joint_position_rad))
    transform=T_trunk_camera(encoders['aahead_yaw_joint'],encoders['aahead_pitch_joint'])
    depth,mask=mask_depth_in_volume(frame.depth,frame.intrinsics,transform)
    return replace(frame,depth=depth),dict(masked_pixels=int(mask.sum()),
        fraction=float(mask.mean()),bounds_trunk_m=DEFAULT_BOUNDS.tolist(),
        source='known carrying profile + head encoders + camera calibration; no simulator object state')
