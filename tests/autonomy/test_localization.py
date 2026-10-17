"""SOFTWARE TESTS: command dead-reckoning + depth scan matching (fixture). Ground truth is used
only to measure error, never as an input to the localizer."""

import numpy as np
import pytest

from autonomy.contracts import LocalizationStatus, Pose2D
from fake_world import Box, FakeRoom, KinematicController
from navigation.localization import ScanMatchLocalizer, distance_field


def walled_room(start=Pose2D(1.0, 1.0, 0.0)):
    W, H, t = 10.0, 8.0, 0.15
    boxes = [
        Box(90, "wall", np.array([0, 0, 0.0]), np.array([W, t, 2.0])),
        Box(91, "wall", np.array([0, H - t, 0.0]), np.array([W, H, 2.0])),
        Box(92, "wall", np.array([0, 0, 0.0]), np.array([t, H, 2.0])),
        Box(93, "wall", np.array([W - t, 0, 0.0]), np.array([W, H, 2.0])),
        Box(2, "wall", np.array([4.0, 0.0, 0.0]), np.array([4.2, 4.5, 2.0])),
        Box(11, "table", np.array([6.0, 1.0, 0.0]), np.array([7.0, 1.8, 0.75])),
        Box(12, "table", np.array([6.0, 5.6, 0.0]), np.array([7.0, 6.4, 0.75])),
        Box(13, "table", np.array([8.4, 3.2, 0.0]), np.array([9.4, 4.0, 0.75])),
        Box(1, "counter", np.array([0.2, 6.6, 0.0]), np.array([2.5, 7.6, 1.0])),
    ]
    room = FakeRoom(boxes, bounds=(0, 0, W, H), start=start)
    room.emit_segmentation = False
    return room


def test_distance_field_is_metric():
    room = walled_room()
    df = distance_field(room.grid())
    g = room.grid()
    assert df[g.world_to_cell((2.0, 0.12))] == 0.0  # wall surface cell (interior cells are not zero)
    assert abs(df[g.world_to_cell((2.05, 1.05))] - 0.9) < 0.12  # ~0.9 m above the bottom wall cells


def _drive(room, waypoints, tracking_scale, seed=0, localize=True):
    rng = np.random.default_rng(seed)
    loc = ScanMatchLocalizer(room.grid(), room.true_pose)
    dr = np.array([room.true_pose.x, room.true_pose.y, room.true_pose.yaw])  # pure dead reckoning
    ctrl = KinematicController(room)
    from autonomy.contracts import AutonomyCommand, CommandKind
    errs, dr_errs, k = [], [], 0
    for i, (x, y, yaw) in enumerate(waypoints):
        cmd = AutonomyCommand(CommandKind.NAVIGATE, float(i), 1e9, Pose2D(x, y, yaw), None, 0.35)
        for _ in range(400):
            p0 = room.true_pose
            fb = ctrl.step(cmd)
            # True body-frame twist from consecutive true poses (the point-robot fixture snaps its
            # heading without reporting it in room.twist, which no real odometry would do).
            p1 = room.true_pose
            c0, s0 = np.cos(p0.yaw), np.sin(p0.yaw)
            dx, dy = p1.x - p0.x, p1.y - p0.y
            true_tw = np.array([c0 * dx + s0 * dy, -s0 * dx + c0 * dy,
                                np.angle(np.exp(1j * (p1.yaw - p0.yaw)))]) / ctrl.dt
            # robot only knows the *commanded* motion; true tracking differs (scale + noise)
            v_cmd = true_tw / tracking_scale + rng.normal(0, 0.02, 3)
            loc.predict(v_cmd, ctrl.dt)
            c, s = np.cos(dr[2]), np.sin(dr[2])
            dr += np.array([(c * v_cmd[0] - s * v_cmd[1]) * ctrl.dt, (s * v_cmd[0] + c * v_cmd[1]) * ctrl.dt,
                            v_cmd[2] * ctrl.dt])
            if localize and k % 1 == 0:
                loc.correct(room.observe())
            k += 1
            p = room.true_pose
            errs.append(np.hypot(loc.pose[0] - p.x, loc.pose[1] - p.y))
            dr_errs.append(np.hypot(dr[0] - p.x, dr[1] - p.y))
            if fb.status.value == "reached":
                break
    return loc, np.array(errs), np.array(dr_errs)


# Each waypoint's heading points along the NEXT leg (turn, then walk forward like a humanoid);
# the point-robot fixture otherwise walks sideways for metres, which isn't how K1 navigates.
ROUTE = [(3.0, 1.2, np.pi / 2), (3.0, 5.5, -0.2), (5.5, 5.0, -0.8), (7.5, 3.0, -0.6), (8.0, 2.2, 0.0)]


def test_scan_matching_bounds_error_while_dead_reckoning_drifts():
    room = walled_room()
    loc, errs, dr_errs = _drive(room, ROUTE, tracking_scale=0.6)  # robot moves 60% of what it's told
    assert dr_errs.max() > 1.0, "test premise: command dead reckoning must drift badly"
    assert errs.max() < 0.25 and np.median(errs) < 0.08
    est = loc.estimate(room.t)
    assert est.provenance.value == "estimated" and est.status != LocalizationStatus.LOST


def test_featureless_view_reports_uncertainty_instead_of_inventing_pose():
    room = FakeRoom([Box(90, "wall", np.array([0, 0, 0.0]), np.array([30, 0.15, 2.0]))],
                    bounds=(-1, -1, 31, 9), start=Pose2D(5.0, 4.0, 0.0))  # looking down an open hall
    room.emit_segmentation = False
    loc = ScanMatchLocalizer(room.grid(), room.true_pose)
    for _ in range(30):
        loc.predict((0.3, 0.0, 0.0), 0.2)
        loc.correct(room.observe())
    assert loc.status in (LocalizationStatus.DEGRADED, LocalizationStatus.LOST)
    assert np.sqrt(loc.cov[0, 0]) > 0.15  # uncertainty grew along the unobservable direction


def test_relocalizes_from_large_initial_error_when_view_constrains_pose():
    room = walled_room(Pose2D(2.0, 2.0, -0.5))  # sees the bottom wall + partition corner: x, y, yaw observable
    loc = ScanMatchLocalizer(room.grid(), Pose2D(3.0, 2.6, -0.2), initial_sigma=(0.8, 0.8, 0.3))  # ~1.2 m off
    for _ in range(4):
        loc.correct(room.observe())
    err = np.hypot(loc.pose[0] - 2.0, loc.pose[1] - 2.0)
    assert err < 0.15 and abs(loc.pose[2] + 0.5) < 0.05, (loc.pose, loc.last_reloc)


def test_single_wall_view_never_claims_ok_while_wrong():
    """Facing only the partition, y is unobservable: the localizer may stay wrong in y but must not
    report OK (the executive then holds/scans instead of navigating on a bad pose)."""
    room = walled_room(Pose2D(2.0, 2.0, 0.3))
    loc = ScanMatchLocalizer(room.grid(), Pose2D(3.0, 2.6, 0.0), initial_sigma=(0.8, 0.8, 0.3))
    for _ in range(4):
        loc.correct(room.observe())
    err = np.hypot(loc.pose[0] - 2.0, loc.pose[1] - 2.0)
    assert err > 0.3  # premise: genuinely ambiguous
    assert loc.status != LocalizationStatus.OK and 1 in loc.last_match["unconstrained_axes"]


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN FAILURE (2026-10-17): with the plant tracking only 60% of commands, turn-in-place scans "
    "over-predict yaw; in open views the scan matcher cannot pin yaw, so real tables are mapped in "
    "the wrong place (smeared track + phantom table/counter) and the executive correctly reports "
    "AMBIGUOUS instead of delivering. Needs: yaw from IMU/leg odometry (not commands), online "
    "tracking-scale estimation, and a wider yaw relocalization when the executive SCANs."))
def test_closed_loop_on_estimated_pose_only():
    """Executive (deployable=True) never sees ground truth: pose = this localizer's estimate from
    commanded velocities + depth; perception = depth geometry. The plant tracks only 60% of each
    command. Truth is used by the fixture renderer/plant and to score the result. Synthetic fixture:
    software evidence only."""
    from autonomy.contracts import DeliveryTask, Outcome, Provenance
    from autonomy.grounding import parse_instruction
    from autonomy.session import AutonomySession
    from perception.tabletop import TabletopDetector

    room = walled_room(Pose2D(1.0, 1.0, 0.0))
    room.boxes = [b for b in room.boxes if b.seg_id != 12 and b.seg_id != 13 and b.label != "counter"]  # one table
    grid = room.grid()
    text = "deliver the pizza and drink to the table"
    s = AutonomySession(DeliveryTask(text, parse_instruction(text), 0.0, 300), grid, TabletopDetector(),
                        deployable=True)
    loc = ScanMatchLocalizer(grid, room.true_pose, initial_sigma=(0.05, 0.05, 0.03))
    dt, k, track = 0.02, 0, 0.6
    v = (0.0, 0.0, 0.0)
    errs = []
    while room.t < 300 and not s.done:
        loc.predict(v, dt)
        obs = None
        if k % 10 == 0:
            obs = room.observe()
            loc.correct(obs)
            obs.pose = loc.estimate(room.t)  # replaces the fixture's privileged pose
            assert obs.pose.provenance == Provenance.ESTIMATED
        v = s.tick(obs, room.t, dt)
        p = room.true_pose
        a, b, w = v[0] * track, v[1] * track, v[2] * track
        c, sn = np.cos(p.yaw), np.sin(p.yaw)
        room.true_pose = Pose2D(p.x + (c * a - sn * b) * dt, p.y + (sn * a + c * b) * dt, p.yaw + w * dt)
        room.twist = np.array([a, b, w])
        room.t += dt
        k += 1
        errs.append(np.hypot(loc.pose[0] - room.true_pose.x, loc.pose[1] - room.true_pose.y))
    assert s.outcome == Outcome.DELIVERED, [e.msg for e in s.events][-8:]
    t = next(b for b in room.boxes if b.label == "table")
    pxy = room.true_pose.xy()
    assert 0.2 <= np.linalg.norm(np.clip(pxy, t.lo[:2], t.hi[:2]) - pxy) <= 0.9
    assert max(errs) < 0.3
    assert all(o.provenance == {Provenance.ESTIMATED} for o in s.executive.memory.objects.values())
