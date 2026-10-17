"""Decoration must not silently change a free payload's physical dynamics."""
import mujoco
import numpy as np
from sim.k1_hand_carry import make_model
from sim.k1_mujoco_appearance import decorate_payload


def test_printed_payload_preserves_inertia_contacts_and_free_dynamics(tmp_path):
    path = tmp_path / 'payload.xml'
    make_model(path, handle_seats=True)
    before = mujoco.MjModel.from_xml_path(str(path))
    decorate_payload(path)
    after = mujoco.MjModel.from_xml_path(str(path))
    for field in ['body_mass','body_inertia','body_ipos','body_iquat','jnt_type']:
        np.testing.assert_array_equal(getattr(before,field),getattr(after,field))
    for i in range(before.ngeom):
        name = before.geom(i).name
        if not name:
            continue
        j = after.geom(name).id
        for field in ['geom_contype','geom_conaffinity','geom_size','geom_pos','geom_quat','geom_friction']:
            np.testing.assert_array_equal(getattr(before,field)[i],getattr(after,field)[j])
    for i in range(after.ngeom):
        if after.geom(i).name.endswith('_visual'):
            assert after.geom_contype[i] == after.geom_conaffinity[i] == 0
    # Identical starting state and integration, including unsupported settling.
    a,b = mujoco.MjData(before),mujoco.MjData(after)
    for _ in range(100):
        mujoco.mj_step(before,a)
        mujoco.mj_step(after,b)
    np.testing.assert_allclose(a.qpos,b.qpos,atol=1e-10,rtol=0)
    np.testing.assert_allclose(a.qvel,b.qvel,atol=1e-10,rtol=0)
