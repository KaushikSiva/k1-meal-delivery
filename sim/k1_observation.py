"""Real MuJoCo RGB-D adapter for explicitly privileged integration diagnostics.

The renderer emulates a head camera, but localization, base attitude/height and
twist come from simulator state. The entire observation must therefore remain a
diagnostic input; this module does not implement deployable odometry.
"""
from pathlib import Path

import mujoco
import numpy as np

from autonomy.contracts import (
    CameraFrame, CameraIntrinsics, GL_TO_CV, Observation, Pose2D,
    PoseEstimate, Provenance,
)

CAMERA_NAME = "k1_diagnostic_rgbd"
CAMERA_BODY = "head_realsense_rgb_link"


def add_head_camera(spec: mujoco.MjSpec, *, fovy: float = 58.0) -> None:
    """Attach to the official optical link. FOV is an assumption, not calibration."""
    if not 1 < fovy < 179:
        raise ValueError("fovy must be in (1, 179) degrees")
    body = spec.body(CAMERA_BODY)
    if body is None:
        raise ValueError(f"Model lacks official camera link {CAMERA_BODY}")
    # Official link is CV optical; MuJoCo camera is OpenGL (180 degrees about x).
    body.add_camera(name=CAMERA_NAME, quat=[0, 1, 0, 0], fovy=fovy, ipd=0)


def sensor_spec(source: Path, *, fovy: float = 58.0) -> mujoco.MjSpec:
    """Return an editable overlay; never change upstream assets on disk."""
    spec = mujoco.MjSpec.from_file(str(source.resolve()))
    add_head_camera(spec, fovy=fovy)
    return spec


class DiagnosticObservationAdapter:
    def __init__(self, model, *, diagnostic: bool, width=640, height=480):
        if diagnostic is not True:
            raise ValueError("Simulator pose/twist require explicit diagnostic=True")
        self.model = model
        self.camera_id = model.camera(CAMERA_NAME).id
        self.trunk_id = model.body("trunk").id
        self.intrinsics = CameraIntrinsics.from_fovy(
            float(model.cam_fovy[self.camera_id]), width, height)
        self.renderer = mujoco.Renderer(model, height=height, width=width)

    def observe(self, data) -> Observation:
        # Synchronize FK after physics; mj_step can leave position-dependent
        # fields at the previous integration state.
        mujoco.mj_forward(self.model, data)
        R = data.xmat[self.trunk_id].reshape(3, 3)
        p = data.xpos[self.trunk_id]
        yaw = float(np.arctan2(R[1, 0], R[0, 0]))
        pose = Pose2D(float(p[0]), float(p[1]), yaw)
        T_world_gl = np.eye(4)
        T_world_gl[:3, :3] = data.cam_xmat[self.camera_id].reshape(3, 3)
        T_world_gl[:3, 3] = data.cam_xpos[self.camera_id]
        T_base_cv = np.linalg.inv(pose.matrix()) @ T_world_gl @ GL_TO_CV

        self.renderer.disable_depth_rendering()
        self.renderer.update_scene(data, camera=CAMERA_NAME)
        rgb = self.renderer.render().copy()
        self.renderer.enable_depth_rendering()
        try:
            depth = self.renderer.render().copy()
        finally:
            self.renderer.disable_depth_rendering()
        far = float(self.model.vis.map.zfar * self.model.stat.extent)
        depth[(depth >= far * 0.999) | (depth <= 0) | ~np.isfinite(depth)] = np.nan

        # Jacobian of the trunk origin, not its offset center of mass.
        jacp = np.zeros((3, self.model.nv))
        jacr = np.zeros_like(jacp)
        mujoco.mj_jacBody(self.model, data, jacp, jacr, self.trunk_id)
        velocity_world = jacp @ data.qvel
        omega_world = jacr @ data.qvel
        forward_dot = np.cross(omega_world, R[:, 0])
        yaw_rate = (R[0, 0] * forward_dot[1] - R[1, 0] * forward_dot[0]) / max(
            R[0, 0] ** 2 + R[1, 0] ** 2, 1e-12)
        velocity_base = pose.matrix()[:3, :3].T @ velocity_world
        return Observation(
            timestamp=float(data.time),
            camera=CameraFrame(
                timestamp=float(data.time), intrinsics=self.intrinsics,
                T_base_camera=T_base_cv, rgb=rgb, depth=depth,
                # Rendered pixels are sensor emulation; exact extrinsics use GT
                # base attitude/height, so the combined frame is tainted.
                provenance=Provenance.SIM_PRIVILEGED,
            ),
            pose=PoseEstimate(pose, np.zeros((3, 3)), float(data.time),
                              source="sim_gt", provenance=Provenance.SIM_PRIVILEGED),
            base_twist=np.array([velocity_base[0], velocity_base[1], yaw_rate]),
            extra={"diagnostic_only": True, "base_twist_provenance": "sim_privileged",
                   "camera_fovy_source": "assumed_58_deg_unless_overridden",
                   "privileged_inputs": ["map_pose", "base_height_attitude", "base_twist"]},
        )

    def close(self):
        self.renderer.close()
