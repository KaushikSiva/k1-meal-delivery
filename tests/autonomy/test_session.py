"""SOFTWARE TEST: AutonomySession driving a velocity-commanded unicycle at 50 Hz (fixture room),
camera at 10 Hz. Mirrors the k1_walk interface (vx, vy, wz); no gait dynamics."""

import numpy as np

from autonomy.contracts import DeliveryTask, Outcome, Pose2D
from autonomy.grounding import parse_instruction
from autonomy.session import AutonomySession
from fake_world import fixture_detector_2d, restaurant
from test_nominal import REGIONS, assert_delivered_at


def drive(room, session, dt=0.02, cam_every=5, max_s=300.0, track_gain=1.0):
    k = 0
    while room.t < max_s and not session.done:
        obs = room.observe() if k % cam_every == 0 else None
        vx, vy, wz = session.tick(obs, room.t, dt)
        a, b = vx * track_gain, vy * track_gain  # track_gain < 1 emulates poor velocity tracking
        p = room.true_pose
        c, s = np.cos(p.yaw), np.sin(p.yaw)
        room.true_pose = Pose2D(p.x + (c * a - s * b) * dt, p.y + (s * a + c * b) * dt, p.yaw + wz * dt)
        room.twist = np.array([a, b, wz])
        room.t += dt
        k += 1
    return session


def make_session(room, **kw):
    text = "deliver the pizza and drink to table 3"
    task = DeliveryTask(text, parse_instruction(text), room.t, 300)
    return AutonomySession(task, room.grid(), fixture_detector_2d(room), REGIONS, **kw)


def test_session_delivers_with_velocity_commands():
    room = restaurant()
    s = drive(room, make_session(room))
    assert_delivered_at(room, s.executive, 13)
    v = np.array([h[1:4] for h in s.history])
    assert np.hypot(v[:, 0], v[:, 1]).max() <= 0.35 + 1e-9
    assert np.all(np.abs(np.diff(np.hypot(v[:, 0], v[:, 1]))) <= 0.25 * 0.02 + 1e-9)  # accel bound
    assert np.abs(v[-1]).max() < 1e-6  # stopped


def test_session_tolerates_poor_velocity_tracking():
    """Codex's diagnostic showed ~0.03 m/s achieved at 0.2 m/s commanded at low speed; here the
    plant achieves only 50% of every command. The closed loop must still arrive and stop."""
    room = restaurant()
    s = drive(room, make_session(room), track_gain=0.5, max_s=300.0)
    assert_delivered_at(room, s.executive, 13)


def test_ticks_between_frames_are_not_sensor_failures():
    """Regression from the K1 MuJoCo trial: camera and executive at the same nominal rate with
    timing jitter made the session call step(None) and enter SENSOR_WAIT."""
    room = restaurant()
    s = make_session(room)
    drive(room, s, cam_every=10, max_s=300.0)  # 5 Hz camera, 50 Hz control
    assert not any("sensor" in e.msg for e in s.events)
    assert_delivered_at(room, s.executive, 13)
