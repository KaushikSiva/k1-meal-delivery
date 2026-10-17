"""Physical structure and unsupported free-fall checks for the hand carry model."""
import mujoco
import numpy as np
from sim.k1_hand_carry import make_model


def test_payload_is_free_and_mass_accounting_matches(tmp_path):
    path = tmp_path / 'carry.xml'
    setup = make_model(path, handle_seats=True)
    m = mujoco.MjModel.from_xml_path(str(path))
    assert m.neq == 0
    for body, joint, mass in [('free_tray','tray_free',.68),
                              ('pizza_box','pizza_free',.8), ('drink','drink_free',.5)]:
        assert m.body(body).parentid[0] == 0
        assert m.joint(joint).type[0] == mujoco.mjtJoint.mjJNT_FREE
        assert np.isclose(m.body(body).mass[0], mass)
    assert not setup['torso_bracket'] and not setup['tray_fixed_joint']


def test_without_contacts_tray_falls_under_gravity(tmp_path):
    path = tmp_path / 'carry.xml'
    make_model(path, handle_seats=True)
    m = mujoco.MjModel.from_xml_path(str(path))
    # Remove all contacts as a diagnostic intervention. A hidden attachment or
    # kinematic tray would fail the ballistic acceleration check.
    m.geom_contype[:] = 0
    m.geom_conaffinity[:] = 0
    d = mujoco.MjData(m)
    q = m.joint('tray_free').qposadr[0]
    v = m.joint('tray_free').dofadr[0]
    initial = float(d.qpos[q+2])
    for _ in range(25):
        mujoco.mj_step(m, d)
    assert np.isclose(d.qvel[v+2], -9.81 * d.time, atol=1e-7)
    assert abs(d.qpos[q+2] - (initial - .5*9.81*d.time**2)) < .001
