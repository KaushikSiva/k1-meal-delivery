"""Real-render geometry/provenance checks; not robotics performance evidence."""
from pathlib import Path

import numpy as np
import pytest

mujoco = pytest.importorskip("mujoco")
from autonomy.contracts import GL_TO_CV, PrivilegedInputError
from sim.k1_observation import CAMERA_BODY, CAMERA_NAME, DiagnosticObservationAdapter, sensor_spec

XML = Path(__file__).resolve().parents[2] / "sim/vendor/booster_assets/robots/K1/K1_22dof.xml"
pytestmark = pytest.mark.skipif(not XML.exists(), reason="official model unavailable")


@pytest.mark.parametrize("yaw,pitch", [(0, 0), (0.7, -0.2), (-1, 0.6)])
def test_render_camera_tracks_articulated_optical_link(yaw, pitch):
    model = sensor_spec(XML).compile()
    data = mujoco.MjData(model)
    data.qpos[model.jnt_qposadr[model.joint("aahead_yaw_joint").id]] = yaw
    data.qpos[model.jnt_qposadr[model.joint("aahead_pitch_joint").id]] = pitch
    mujoco.mj_forward(model, data)
    cam, body = model.camera(CAMERA_NAME).id, model.body(CAMERA_BODY).id
    np.testing.assert_allclose(data.cam_xpos[cam], data.xpos[body], atol=1e-9)
    np.testing.assert_allclose(data.cam_xmat[cam].reshape(3, 3) @ GL_TO_CV[:3, :3],
                               data.xmat[body].reshape(3, 3), atol=1e-9)


def test_real_render_is_metric_z_depth_and_cannot_be_deployed():
    spec = sensor_spec(XML)
    initial = spec.compile()
    state = mujoco.MjData(initial)
    mujoco.mj_forward(initial, state)
    cam = initial.camera(CAMERA_NAME).id
    R = state.cam_xmat[cam].reshape(3, 3)
    center = state.cam_xpos[cam] - 2 * R[:, 2]
    # Flat target perpendicular to optical axis, front surface exactly 2 m away.
    quat = np.zeros(4)
    mujoco.mju_mat2Quat(quat, R.ravel())
    spec.worldbody.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX,
                            pos=center - 0.01 * R[:, 2], quat=quat,
                            size=[2, 2, 0.01], rgba=[1, 0, 0, 1])
    model = spec.compile()
    data = mujoco.MjData(model)
    with pytest.raises(ValueError, match="diagnostic"):
        DiagnosticObservationAdapter(model, diagnostic=False)
    adapter = DiagnosticObservationAdapter(model, diagnostic=True, width=320, height=240)
    try:
        obs = adapter.observe(data)
        assert obs.camera.rgb.shape == (240, 320, 3)
        assert obs.camera.rgb.dtype == np.uint8
        # Both central and off-axis samples read z depth, not longer ray length.
        assert obs.camera.depth[120, 160] == pytest.approx(2, abs=0.01)
        assert obs.camera.depth[120, 220] == pytest.approx(2, abs=0.01)
        assert obs.camera.segmentation is None
        assert obs.pose.source == "sim_gt"
        with pytest.raises(PrivilegedInputError):
            obs.assert_deployable()
        np.testing.assert_allclose(obs.base_twist, 0, atol=1e-10)
        # Root translation is in world coordinates; autonomy twist is in base.
        data.qpos[3:7] = [np.sqrt(0.5), 0, 0, np.sqrt(0.5)]
        data.qvel[:6] = [0, 0.2, 0, 0, 0, 0.3]
        turned = adapter.observe(data)
        assert turned.pose.pose.yaw == pytest.approx(np.pi / 2)
        np.testing.assert_allclose(turned.base_twist, [0.2, 0, 0.3], atol=1e-9)
    finally:
        adapter.close()
