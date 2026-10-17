"""K1 head-camera extrinsics from the official Booster model (pure numpy, no simulator).

Chain (booster_assets K1_22dof.xml @ 12a97516, frames verified against MuJoCo FK in
tests/autonomy/test_k1_camera.py):
    trunk -> aahead_yaw_link   pos (0.0056, 0, 0.2149), joint axis z, range [-1.012, 1.012]
          -> aahead_pitch_link pos (0, 0, 0.033),       joint axis y, range [-0.314, 0.794]
          -> head_realsense_rgb_link / head_booster_stereo_rgb_link (fixed)
Both camera link frames are already OpenCV optical frames (z forward, x right, y down).
At neutral head the RealSense optical axis is pitched ~15.2 deg down; the stereo is level.

Intrinsics are NOT in the model and the exact camera SKU is unverified: use calibration.
Trunk height while walking in Codex's MuJoCo diagnostic was ~0.545 m (camera ~0.9 m); that is
one sim run, not a measurement of the real robot.
"""

from __future__ import annotations

import numpy as np

HEAD_YAW_RANGE = (-1.012, 1.012)
HEAD_PITCH_RANGE = (-0.314, 0.794)
MJCF_SOURCE = "BoosterRobotics/booster_assets@12a97516f57469078707afb587a5f84c1cb110d1 robots/K1/K1_22dof.xml"

_T_TRUNK_YAW = np.array([0.0056, 0.0, 0.2149])
_T_YAW_PITCH = np.array([0.0, 0.0, 0.033])
CAMERAS = {  # pos, quat (w, x, y, z) in aahead_pitch_link
    "realsense": (np.array([0.053617, -0.0115, 0.10231]), np.array([0.42967577, -0.56158605, 0.56158587, -0.42967563])),
    "stereo": (np.array([0.060138, 0.0351, 0.092774]), np.array([0.50000016, -0.5, 0.49999984, -0.5])),
}


def quat_to_R(q) -> np.ndarray:
    w, x, y, z = np.asarray(q, float) / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def _T(R=np.eye(3), p=(0, 0, 0)) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = R, p
    return T


def _rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _ry(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def T_trunk_camera(head_yaw: float = 0.0, head_pitch: float = 0.0, camera: str = "realsense") -> np.ndarray:
    """Optical camera frame -> trunk frame, from head joint angles (encoders)."""
    pos, quat = CAMERAS[camera]
    return _T(p=_T_TRUNK_YAW) @ _T(_rz(head_yaw)) @ _T(p=_T_YAW_PITCH) @ _T(_ry(head_pitch)) @ _T(quat_to_R(quat), pos)


def T_base_camera(head_yaw: float, head_pitch: float, trunk_height: float, trunk_roll: float = 0.0,
                  trunk_pitch: float = 0.0, camera: str = "realsense") -> np.ndarray:
    """Optical -> autonomy `base` frame (floor under trunk, gravity-aligned, yaw = trunk yaw).
    trunk_height / roll / pitch must come from the robot's own estimate (IMU + leg kinematics),
    never from simulator ground truth on the actor path."""
    T_base_trunk = _T(_ry(trunk_pitch) @ _rx(trunk_roll), (0.0, 0.0, trunk_height))
    return T_base_trunk @ T_trunk_camera(head_yaw, head_pitch, camera)
