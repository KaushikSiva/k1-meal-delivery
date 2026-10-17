from pathlib import Path
import json
import numpy as np
import pytest
from autonomy.contracts import CameraFrame, CameraIntrinsics, Pose2D, PoseEstimate, Provenance
from contracts.robot_telemetry import RobotTelemetry, RelativeHeading
from sim.k1_sensor_observation import SensorCameraGeometry, SensorObservationAdapter


def test_camera_extrinsics_use_encoders_and_relative_attitude_only():
    mujoco = pytest.importorskip('mujoco')
    root = Path(__file__).resolve().parents[2]
    path = root / 'sim/vendor/booster_assets/robots/K1/K1_22dof.xml'
    geometry = SensorCameraGeometry(path)
    cfg = json.loads((root / 'sim/k1_isaac_nominal.json').read_text())['joints']
    names = geometry.legs.names
    for hy, hp in [(0., 0.), (.3, -.1), (-.4, .5)]:
        q = np.array([cfg[n]['position'] for n in names])
        q[names.index('aahead_yaw_joint')] = hy
        q[names.index('aahead_pitch_joint')] = hp
        t = RobotTelemetry(1., names, q, np.zeros(22), np.zeros(3), np.zeros(3), 'fixture')
        h = RelativeHeading(1., 0., .01, (1., 0., 0., 0.), 1.)
        actual, height = geometry.extrinsics(t, h)
        model = mujoco.MjModel.from_xml_path(str(path)); data = mujoco.MjData(model)
        data.qpos[:3] = [9., -7., height]
        # Arbitrary global translation/yaw are evaluation-only.
        angle = .8
        data.qpos[3:7] = [np.cos(angle/2), 0, 0, np.sin(angle/2)]
        for n, v in zip(names, q): data.qpos[model.joint(n).qposadr[0]] = v
        mujoco.mj_forward(model, data)
        link = model.body('head_realsense_rgb_link').id
        world = np.eye(4); world[:3, :3] = data.xmat[link].reshape(3, 3); world[:3, 3] = data.xpos[link]
        expected = np.linalg.inv(Pose2D(9., -7., angle).matrix()) @ world
        np.testing.assert_allclose(actual, expected, atol=1e-6)


def test_sensor_assembly_rejects_privileged_pose_and_invalid_twist():
    frame = CameraFrame(1., CameraIntrinsics.from_fovy(58., 64, 48), np.eye(4),
                        rgb=np.zeros((48,64,3),np.uint8), provenance=Provenance.ESTIMATED)
    pose = PoseEstimate(Pose2D(0.,0.,0.), np.eye(3), 1., 'fixture', Provenance.ESTIMATED)
    obs = SensorObservationAdapter.assemble(frame, pose, [0,0,0])
    assert obs.extra['leg_translation_used'] is False
    with pytest.raises(ValueError, match='twist'):
        SensorObservationAdapter.assemble(frame, pose, [np.nan,0,0])
    gt = PoseEstimate(pose.pose, pose.cov, 1., 'sim_gt', Provenance.SIM_PRIVILEGED)
    with pytest.raises(ValueError, match='privileged'):
        SensorObservationAdapter.assemble(frame, gt, [0,0,0])
