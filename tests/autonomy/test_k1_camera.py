"""Checks perception/k1_camera.py against MuJoCo forward kinematics of the official K1 model.
Software/geometry test only. Skipped if mujoco or the vendored asset is unavailable."""

from pathlib import Path

import numpy as np
import pytest

from perception.k1_camera import T_trunk_camera

ROOT = Path(__file__).resolve().parents[2]
XML = ROOT / "sim/vendor/booster_assets/robots/K1/K1_22dof.xml"
mujoco = pytest.importorskip("mujoco")


@pytest.mark.skipif(not XML.exists(), reason="vendored K1 asset not present")
@pytest.mark.parametrize("cam,body", [("realsense", "head_realsense_rgb_link"), ("stereo", "head_booster_stereo_rgb_link")])
@pytest.mark.parametrize("yaw,pitch", [(0.0, 0.0), (0.7, -0.2), (-1.0, 0.6)])
def test_matches_mujoco_fk(cam, body, yaw, pitch):
    m = mujoco.MjModel.from_xml_path(str(XML))
    d = mujoco.MjData(m)
    d.qpos[m.jnt_qposadr[m.joint("aahead_yaw_joint").id]] = yaw
    d.qpos[m.jnt_qposadr[m.joint("aahead_pitch_joint").id]] = pitch
    mujoco.mj_forward(m, d)
    tr, cb = m.body("trunk").id, m.body(body).id
    T_w_tr = np.eye(4); T_w_tr[:3, :3] = d.xmat[tr].reshape(3, 3); T_w_tr[:3, 3] = d.xpos[tr]
    T_w_c = np.eye(4); T_w_c[:3, :3] = d.xmat[cb].reshape(3, 3); T_w_c[:3, 3] = d.xpos[cb]
    np.testing.assert_allclose(np.linalg.inv(T_w_tr) @ T_w_c, T_trunk_camera(yaw, pitch, cam), atol=1e-6)


def test_optical_convention_at_neutral():
    R = T_trunk_camera(0, 0, "realsense")[:3, :3]
    assert R[:, 2][0] > 0.9 and R[:, 2][2] < 0  # looks forward and down
    assert np.degrees(np.arcsin(-R[2, 2])) == pytest.approx(15.2, abs=0.2)
    assert R[:, 1][2] < -0.9  # image y points down
