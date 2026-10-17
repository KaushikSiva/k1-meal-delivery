"""Rendered RGB-D with sensor-derived extrinsics, excluding simulator root state.

The renderer necessarily uses the simulated scene to produce pixels. Only those
pixels cross this boundary; camera world transforms, root pose and root velocity
are never read here. Flat floor, stance and initial level attitude are explicit
estimator assumptions, not hardware calibration.
"""
from pathlib import Path
import numpy as np

from autonomy.contracts import CameraFrame, CameraIntrinsics, Observation, Provenance
from contracts.robot_telemetry import RobotTelemetry, RelativeHeading
from deployment.k1_leg_estimator import K1LegEstimator
from perception.k1_camera import T_base_camera
from sim.k1_observation import CAMERA_NAME


class SensorCameraGeometry:
    def __init__(self, model_path: Path):
        self.legs = K1LegEstimator(model_path)

    def extrinsics(self, telemetry: RobotTelemetry, heading: RelativeHeading):
        if heading.provenance != Provenance.ESTIMATED:
            raise ValueError('Relative heading must be estimated from sensors')
        body = self.legs.estimate(telemetry, heading)
        positions = dict(zip(telemetry.joint_names, telemetry.joint_position_rad))
        transform = T_base_camera(
            positions['aahead_yaw_joint'], positions['aahead_pitch_joint'],
            body.trunk_height_m, body.trunk_roll_rad, body.trunk_pitch_rad)
        # Deliberately exclude the leg velocity: its real walking diagnostic failed.
        return transform, body.trunk_height_m


class SensorObservationAdapter:
    def __init__(self, model, model_path: Path, *, width=640, height=480):
        import mujoco
        self.mujoco = mujoco
        camera_id = model.camera(CAMERA_NAME).id
        self.intrinsics = CameraIntrinsics.from_fovy(
            float(model.cam_fovy[camera_id]), width, height)
        self.geometry = SensorCameraGeometry(model_path)
        self.renderer = mujoco.Renderer(model, height=height, width=width)
        self.far = float(model.vis.map.zfar * model.stat.extent)

    def capture(self, data, telemetry: RobotTelemetry, heading: RelativeHeading):
        if abs(float(data.time) - telemetry.timestamp) > 1e-6:
            raise ValueError('Camera and telemetry must be synchronized')
        transform, height = self.geometry.extrinsics(telemetry, heading)
        self.renderer.disable_depth_rendering()
        self.renderer.update_scene(data, camera=CAMERA_NAME)
        rgb = self.renderer.render().copy()
        self.renderer.enable_depth_rendering()
        try:
            depth = self.renderer.render().copy()
        finally:
            self.renderer.disable_depth_rendering()
        depth[(depth >= self.far * .999) | (depth <= 0) | ~np.isfinite(depth)] = np.nan
        frame = CameraFrame(telemetry.timestamp, self.intrinsics, transform,
                            rgb=rgb, depth=depth, provenance=Provenance.ESTIMATED)
        return frame, height

    @staticmethod
    def assemble(frame, pose, estimated_twist):
        if frame.provenance != Provenance.ESTIMATED or pose.provenance != Provenance.ESTIMATED:
            raise ValueError('Sensor navigation rejects privileged camera/pose')
        twist = np.asarray(estimated_twist, float)
        if twist.shape != (3,) or not np.isfinite(twist).all():
            raise ValueError('Invalid estimated twist')
        return Observation(frame.timestamp, frame, pose, twist.copy(), extra={
            'base_twist_provenance': 'estimated',
            'camera_extrinsic_source': 'head_encoders+gyro_attitude+leg_height',
            'camera_fovy_source': 'assumed_58_deg_unless_overridden',
            'assumptions': ['level initial attitude', 'flat floor', 'stance foot for height'],
            'leg_translation_used': False,
        })

    def close(self):
        self.renderer.close()
