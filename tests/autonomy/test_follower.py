"""SOFTWARE TESTS: path follower on an ideal unicycle (no gait dynamics)."""

import numpy as np

from autonomy.contracts import AutonomyCommand, CommandKind, Pose2D
from navigation.follower import FollowerLimits, PathFollower


def integrate(pose, v, dt):
    c, s = np.cos(pose.yaw), np.sin(pose.yaw)
    return Pose2D(pose.x + (c * v[0] - s * v[1]) * dt, pose.y + (s * v[0] + c * v[1]) * dt, pose.yaw + v[2] * dt)


def drive(cmd_fn, pose, T=40.0, dt=0.02):
    f, log = PathFollower(), []
    t = 0.0
    while t < T:
        cmd = cmd_fn(t)
        v = f.step(cmd, pose, t, dt)
        pose = integrate(pose, v, dt)
        log.append((t, v.copy(), pose))
        t += dt
    return pose, log


def test_reaches_goal_with_bounded_accel_and_smooth_stop():
    goal = Pose2D(3.0, 1.0, np.pi / 2)
    mk = lambda t: AutonomyCommand(CommandKind.FINAL_APPROACH, t, t + 1.0, goal, ((0, 0), (3.0, 0.0)), 0.3)
    pose, log = drive(mk, Pose2D(0, 0, 0))
    assert np.hypot(pose.x - 3, pose.y - 1) < 0.08 and abs(np.angle(np.exp(1j * (pose.yaw - goal.yaw)))) < 0.1
    vs = np.array([v for _, v, _ in log])
    acc = np.abs(np.diff(vs[:, 0])) / 0.02
    lim = FollowerLimits()
    assert acc.max() <= lim.final_accel + 1e-6
    assert vs[:, 0].max() <= 0.3 + 1e-9 and np.abs(vs[-1]).max() < 1e-3


def test_hold_and_expiry_decelerate_not_step():
    goal = Pose2D(10.0, 0.0, 0.0)
    nav = lambda t: AutonomyCommand(CommandKind.NAVIGATE, t, t + 1.0, goal, None, 0.35)
    stale = AutonomyCommand(CommandKind.NAVIGATE, 0.0, 1.0, goal, None, 0.35)  # never refreshed
    f = PathFollower()
    pose = Pose2D(0, 0, 0)
    for i in range(400):  # cruise
        pose = integrate(pose, f.step(nav(i * 0.02), pose, i * 0.02, 0.02), 0.02)
    assert f.v[0] > 0.3
    speeds = []
    for i in range(100):  # command expired -> ramp down
        speeds.append(f.step(stale, pose, 10.0 + i * 0.02, 0.02)[0])
    d = np.diff([0.35] + speeds)
    assert np.all(d <= 1e-9) and np.all(np.abs(d) <= FollowerLimits().accel * 0.02 + 1e-9) and speeds[-1] == 0


def test_planar_norm_cap_includes_reverse_and_lateral():
    # Codex review repro: goal slightly behind-left with max_speed=0 must not translate.
    f = PathFollower()
    pose = Pose2D(0, 0, 0)
    for i in range(100):
        cmd = AutonomyCommand(CommandKind.NAVIGATE, i * 0.02, i * 0.02 + 1, Pose2D(-0.1, 0.1, 0.0), None, 0.0)
        v = f.step(cmd, pose, i * 0.02, 0.02)
        assert np.hypot(v[0], v[1]) <= 1e-12
    for cap in (0.05, 0.1):
        f = PathFollower()
        for i in range(300):
            cmd = AutonomyCommand(CommandKind.NAVIGATE, 0.0, 1e9, Pose2D(-0.25, 0.25, 0.0), None, cap)
            v = f.step(cmd, Pose2D(0, 0, 0), i * 0.02, 0.02)
            assert np.hypot(v[0], v[1]) <= cap + 1e-9


def test_cap_reduction_ramps_down_at_accel_limit():
    f = PathFollower()
    goal = Pose2D(20, 0, 0)
    for i in range(300):
        f.step(AutonomyCommand(CommandKind.NAVIGATE, 0.0, 1e9, goal, None, 0.35), Pose2D(0, 0, 0), i * 0.02, 0.02)
    prev = f.v.copy()
    for i in range(100):
        v = f.step(AutonomyCommand(CommandKind.NAVIGATE, 1.0, 1e9, goal, None, 0.1), Pose2D(0, 0, 0), 6 + i * 0.02, 0.02)
        assert np.linalg.norm(v[:2] - prev[:2]) <= FollowerLimits().accel * 0.02 + 1e-9  # no step, bounded accel
        prev = v.copy()
    assert abs(np.hypot(prev[0], prev[1]) - 0.1) < 1e-9  # converged to the new bounded target


def test_scan_tracks_relative_heading_and_stops():
    f, pose, dt = PathFollower(), Pose2D(0, 0, 0.3), 0.02
    for i in range(500):
        t = i * dt
        cmd = AutonomyCommand(CommandKind.SCAN, 0.0, t + 1.0, scan_yaw=0.8)  # refreshed, same issued_at
        pose = integrate(pose, f.step(cmd, pose, t, dt), dt)
    assert abs(pose.yaw - 1.1) < 0.03 and abs(f.v[2]) < 0.05


def test_direction_change_stays_inside_speed_ball():
    # Codex review repro (19:24Z): per-axis clipping left the cap ball while turning.
    f = PathFollower()
    f.v = np.array([0.245, 0.245, 0.0])  # norm 0.3465 <= cap
    f._track = lambda cmd, pose, accel: np.array([0.34, 0.05, 0.0])  # norm 0.3437 <= cap
    cmd = AutonomyCommand(CommandKind.NAVIGATE, 0.0, 1e9, Pose2D(5, 0, 0), None, 0.35)
    for i in range(40):
        v = f.step(cmd, Pose2D(0, 0, 0), i * 0.02, 0.02)
        assert np.hypot(v[0], v[1]) <= 0.35 + 1e-12


def test_reset_clears_scan_latch_for_reused_issued_at():
    f, dt = PathFollower(), 0.02
    pose = Pose2D(0, 0, 0.0)
    for i in range(300):
        pose = integrate(pose, f.step(AutonomyCommand(CommandKind.SCAN, 0.0, 1e9, scan_yaw=0.5), pose, i * dt, dt), dt)
    f.reset()
    pose2 = Pose2D(0, 0, 2.0)  # new episode, same issued_at=0.0
    for i in range(300):
        pose2 = integrate(pose2, f.step(AutonomyCommand(CommandKind.SCAN, 0.0, 1e9, scan_yaw=0.5), pose2, i * dt, dt), dt)
    assert abs(pose2.yaw - 2.5) < 0.03


def test_deadband_compensation_is_opt_in_and_never_exceeds_cap():
    goal = Pose2D(0.2, 0.0, 0.0)
    cmd = lambda t, cap: AutonomyCommand(CommandKind.FINAL_APPROACH, t, t + 1, goal, None, cap)
    assert FollowerLimits().min_walk_cmd == 0.0  # off by default
    f = PathFollower()  # default: 5 cm from goal the decel profile asks for ~sqrt(2*0.15*0.05) m/s
    for i in range(200):
        v = f.step(cmd(i * 0.02, 0.15), Pose2D(0.15, 0, 0), i * 0.02, 0.02)
    assert 0.08 < v[0] < 0.15  # small command the unloaded k1_walk barely tracks
    on = PathFollower(FollowerLimits(min_walk_cmd=0.3, final_accel=10.0))
    for i in range(50):
        v = on.step(cmd(i * 0.02, 0.15), Pose2D(0.19, 0, 0), i * 0.02, 0.02)  # 1 cm from goal
    assert np.hypot(v[0], v[1]) < 1e-9  # inside stop radius -> exactly zero
    for i in range(50):
        v = on.step(cmd(i * 0.02, 0.15), Pose2D(0.0, 0, 0), i * 0.02, 0.02)
    assert abs(np.hypot(v[0], v[1]) - 0.15) < 1e-9  # raised to min(min_walk, cap): cap still wins
    on2 = PathFollower(FollowerLimits(min_walk_cmd=0.3))  # default accel: profile asks ~0.17 at 0.1 m
    for i in range(200):
        v = on2.step(cmd(i * 0.02, 0.4), Pose2D(0.1, 0, 0), i * 0.02, 0.02)
    assert abs(np.hypot(v[0], v[1]) - 0.3) < 1e-9  # raised to min_walk under a higher cap
