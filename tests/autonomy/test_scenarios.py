"""SOFTWARE TESTS on a synthetic fixture (tests/autonomy/fake_world.py).
They check executive *behavior*; they are not simulator or robot performance evidence."""

import numpy as np
import pytest

from autonomy.contracts import (
    CommandKind,
    DeliveryTask,
    LocalizationStatus,
    Outcome,
    Pose2D,
    PoseEstimate,
    PrivilegedInputError,
    Provenance,
)
from autonomy.executive import DeliveryExecutive, ExecutiveConfig, State
from autonomy.grounding import parse_instruction
from fake_world import Box, KinematicController, fixture_detector_2d, restaurant, run
from memory import SceneMemory
from perception import SimSegmentationDetector
from test_nominal import REGIONS, assert_delivered_at, make


def window(t, t0, t1):
    return t0 <= t < t1


def moved_between(cmds, room_log, t0, t1):
    return max((np.linalg.norm(b - a) for (ta, a), (tb, b) in zip(room_log, room_log[1:]) if t0 <= ta and tb <= t1),
               default=0.0)


# --------------------------------------------------------------------------- occlusion
def test_seen_then_occluded_target_is_kept_in_memory_and_reached():
    # Start with table 3 in view and readable (long-range OCR); a passer-by then blocks the view.
    room = restaurant(start=Pose2D(5.0, 3.6, 0.0))
    person = Box(50, "person", np.array([6.6, 3.0, 0.0]), np.array([6.9, 4.2, 1.9]), in_map=False, solid=False,
                 visible=False)
    room.boxes.append(person)

    def hooks(t, room, ex):
        person.visible = window(t, 1.0, 9.0)

    ex = make(room, ocr_range=6.0)
    stop, cmds, _ = run(ex, room, hooks=hooks)
    assert_delivered_at(room, ex, 13)
    # Confirmed before the occlusion and never fell back to exploring.
    assert not any(c.state == State.SEARCH.value and c.kind == CommandKind.NAVIGATE for c in cmds)
    # Same track before and after the occlusion: exactly one memory entry reads "3".
    assert sum(o.attribute("table_number")[0] == "3" for o in ex.memory.query("table")) == 1


# --------------------------------------------------------------------------- stale memory
def test_stale_memory_is_treated_as_hypothesis_and_corrected_when_target_moved():
    room = restaurant(start=Pose2D(5.0, 3.6, 0.0))
    mem = SceneMemory()
    # Episode 1: just look at table 3 from the start pose (long-range OCR) to populate memory.
    ex0 = make(room, ocr_range=6.0, memory=mem)
    ex0.step(room.observe())
    assert any(o.attribute("table_number")[0] == "3" for o in mem.objects.values())
    # Much later, staff moved table 3 to the top-right corner.
    t3 = next(b for b in room.boxes if b.seg_id == 13)
    t3.lo, t3.hi = np.array([8.6, 6.6, 0.0]), np.array([9.6, 7.4, 0.75])
    room.t += 200.0
    room.true_pose = Pose2D(1.0, 1.0, 0.0)  # robot is elsewhere; old location not in view
    ex = make(room, memory=mem)
    stop, cmds, _ = run(ex, room)
    first = cmds[0]
    assert first.state == State.APPROACH.value and "stale" in first.reason
    assert first.max_speed <= ExecutiveConfig().degraded_speed
    assert any("lost from memory" in e.msg or "reacquire failed" in e.msg for e in ex.events)
    assert_delivered_at(room, ex, 13)


# --------------------------------------------------------------------------- localization
def _pose_log_hooks(lost_from, lost_to, log):
    def hooks(t, room, ex):
        log.append((t, room.true_pose.xy()))
        lost = window(t, lost_from, lost_to)
        room.pose_status = LocalizationStatus.LOST if lost else LocalizationStatus.OK
        room.pose_sigma = 0.8 if lost else 0.03
    return hooks


def test_localization_loss_stops_translation_then_recovers():
    room = restaurant()
    log = []
    ex = make(room)
    stop, cmds, _ = run(ex, room, hooks=_pose_log_hooks(8.0, 16.0, log))
    lost_cmds = [c for c in cmds if 8.0 <= c.issued_at < 16.0]
    assert lost_cmds and all(c.kind in (CommandKind.HOLD, CommandKind.SCAN) for c in lost_cmds)
    # Deceleration allowed for one tick, then no translation while lost.
    assert moved_between(cmds, log, 8.6, 16.0) < 0.05
    assert any("relocalized" in e.msg for e in ex.events)
    assert_delivered_at(room, ex, 13)


def test_localization_never_recovers_reports_failure():
    room = restaurant()
    ex = make(room)
    stop, _, _ = run(ex, room, hooks=_pose_log_hooks(8.0, 1e9, []))
    assert ex.outcome == Outcome.LOCALIZATION_LOST and stop.kind == CommandKind.STOP


def test_degraded_localization_caps_speed_and_blocks_arrival():
    room = restaurant()

    def hooks(t, room, ex):
        room.pose_sigma = 0.25  # between degraded (0.15) and lost (0.4) for the whole run

    ex = make(room, time_limit_s=150)
    ctrl = KinematicController(room)
    stop, cmds, _ = run(ex, room, ctrl, hooks=hooks)
    assert ex.outcome != Outcome.DELIVERED
    assert ctrl.max_speed_seen <= ExecutiveConfig().degraded_speed + 1e-6


# --------------------------------------------------------------------------- ambiguity
def test_ambiguous_destination_is_reported_not_guessed():
    room = restaurant(start=Pose2D(9.0, 1.0, np.deg2rad(140)))  # tables 1 and 2 both in view
    ex = make(room, text="take this to the table")
    stop, _, _ = run(ex, room)
    assert ex.outcome == Outcome.AMBIGUOUS_DESTINATION
    assert stop.kind == CommandKind.STOP


def test_duplicate_table_numbers_are_ambiguous():
    room = restaurant(start=Pose2D(9.0, 1.0, np.deg2rad(140)))  # tables 1 and 2 in view
    for b in room.boxes:
        if b.seg_id in (11, 12):
            b.attributes["table_number"] = "3"  # placard mistake: two tables labeled 3
    ex = make(room, ocr_range=8.0)
    run(ex, room)
    assert ex.outcome == Outcome.AMBIGUOUS_DESTINATION


def test_unparseable_destination_raises():
    with pytest.raises(ValueError):
        parse_instruction("bring the pizza over")


# --------------------------------------------------------------------------- obstacles
def test_hidden_obstacle_blocks_path_and_executive_replans():
    room = restaurant(start=Pose2D(2.0, 6.0, np.deg2rad(-20)))
    # A cart not on the prior map, in the gap above the partition.
    room.boxes.append(Box(60, "cart", np.array([3.6, 4.5, 0.0]), np.array([4.6, 5.5, 0.9]), in_map=False))
    # Live depth layer off: this test covers the contact-feedback (BLOCKED) path specifically.
    ex = make(room, ocr_range=10.0, obstacle_layer=False)
    stop, cmds, _ = run(ex, room)
    assert any("blocked" in e.msg for e in ex.events)
    assert_delivered_at(room, ex, 13)


def test_fully_blocked_route_reports_no_path():
    room = restaurant(start=Pose2D(2.0, 6.0, np.deg2rad(-20)))
    room.boxes.append(Box(60, "barrier", np.array([3.6, 4.5, 0.0]), np.array([4.6, 7.95, 0.9]), in_map=False))
    ex = make(room, ocr_range=10.0)
    stop, _, _ = run(ex, room)
    assert ex.outcome == Outcome.NO_PATH


# --------------------------------------------------------------------------- sensors
def test_camera_dropout_holds_then_resumes():
    room = restaurant()
    log = []

    def hooks(t, room, ex):
        log.append((t, room.true_pose.xy()))
        room.camera_on = not window(t, 6.0, 9.0)

    ex = make(room)
    stop, cmds, _ = run(ex, room, hooks=hooks)
    assert any(c.kind == CommandKind.HOLD and c.state == State.SENSOR_WAIT.value for c in cmds)
    assert moved_between(cmds, log, 6.6, 9.0) < 0.05
    assert_delivered_at(room, ex, 13)


def test_sensor_timeout_reports_failure():
    room = restaurant()

    def hooks(t, room, ex):
        room.camera_on = t < 4.0

    ex = make(room)
    run(ex, room, hooks=hooks)
    assert ex.outcome == Outcome.SENSOR_TIMEOUT


# --------------------------------------------------------------------------- arrival
def test_stable_arrival_requires_dwell_and_low_speed():
    room = restaurant()
    ex = make(room)
    stop, cmds, _ = run(ex, room)
    assert_delivered_at(room, ex, 13)
    final = next(c for c in cmds if c.kind == CommandKind.FINAL_APPROACH)
    assert final.max_speed <= ExecutiveConfig().final_speed
    t_settle = next(e.t for e in ex.events if e.msg == "final_approach -> settle")
    assert stop.issued_at - t_settle >= ExecutiveConfig().settle_s - 1e-6


class JitterController(KinematicController):
    """Base never settles: reports residual velocity while holding (e.g. balance sway)."""

    def step(self, cmd):
        fb = super().step(cmd)
        if cmd.kind == CommandKind.HOLD:
            self.room.twist = np.array([0.12, 0.0, 0.0])
        return fb


def test_no_success_while_base_keeps_moving():
    room = restaurant()
    ex = make(room, time_limit_s=120)
    run(ex, room, JitterController(room))
    assert ex.outcome == Outcome.TIMEOUT


def test_commands_expire_and_are_bounded():
    room = restaurant()
    ex = make(room)
    _, cmds, _ = run(ex, room)
    cfg = ExecutiveConfig()
    for c in cmds:
        if c.kind != CommandKind.STOP:
            assert c.expires_at - c.issued_at <= cfg.verify_hold_s + cfg.command_ttl_s + 1e-9
        assert 0.0 <= c.max_speed <= cfg.approach_speed
        assert c.selected_by == "executive" and c.state


# --------------------------------------------------------------------------- privileged inputs
def test_deployable_mode_rejects_privileged_detector_and_pose():
    room = restaurant()
    task = DeliveryTask("to table 3", parse_instruction("to table 3"), 0.0)
    with pytest.raises(PrivilegedInputError):
        DeliveryExecutive(task, room.grid(), SimSegmentationDetector(), deployable=True)
    ex = DeliveryExecutive(task, room.grid(), fixture_detector_2d(room), deployable=True)
    obs = room.observe()
    obs.camera.segmentation = None
    obs.pose = PoseEstimate(obs.pose.pose, obs.pose.cov, obs.t if hasattr(obs, "t") else 0.0, "sim_gt",
                            Provenance.SIM_PRIVILEGED)
    with pytest.raises(PrivilegedInputError):
        ex.step(obs)


# --------------------------------------------------------------------------- review regressions (Codex 19:18Z)
def _settled_executive():
    room = restaurant()
    ex = make(room)
    run(ex, room)
    assert ex.outcome == Outcome.DELIVERED
    return room, ex


def test_degraded_pose_never_completes_settle():
    room, ex = _settled_executive()
    # Rewind to SETTLE with dwell already satisfied, then feed a degraded pose.
    ex.state, ex.outcome = State.SETTLE, None
    ex.ctx.settle_since = room.t - 10.0
    room.pose_sigma = 0.25
    for _ in range(20):
        room.t += 0.2
        cmd = ex.step(room.observe())
        assert ex.outcome != Outcome.DELIVERED and cmd.kind != CommandKind.STOP
    assert ex.ctx.settle_since is None
    room.pose_sigma = 0.03  # recovered: needs a fresh full dwell
    t_ok = room.t
    while ex.outcome is None:
        room.t += 0.2
        ex.step(room.observe())
    assert ex.outcome == Outcome.DELIVERED and room.t - t_ok >= ExecutiveConfig().settle_s - 1e-6


def test_stale_future_and_nonfinite_inputs_are_rejected():
    room = restaurant()
    ex = make(room)
    room.t = 2.0
    obs = room.observe()
    obs.pose = PoseEstimate(obs.pose.pose, obs.pose.cov, -100.0, "odom")  # pose 102 s old
    assert ex.step(obs).kind == CommandKind.HOLD and ex.state == State.SENSOR_WAIT
    room.t = 2.2
    obs = room.observe()
    obs.camera.timestamp = 50.0  # future camera frame
    ex.step(obs)
    assert ex.state == State.SENSOR_WAIT
    room.t = 2.4
    obs = room.observe()
    obs.pose = PoseEstimate(Pose2D(np.nan, 0, 0), obs.pose.cov, obs.timestamp, "odom")
    ex.step(obs)
    assert ex.state == State.SENSOR_WAIT
    room.t = 2.6
    good = room.observe()
    ex.step(good)
    assert ex.state != State.SENSOR_WAIT
    ex.step(good)  # same snapshot again (non-monotonic) -> rejected
    assert ex.state == State.SENSOR_WAIT


def test_independent_clock_reaches_sensor_timeout_without_snapshots():
    room = restaurant()
    ex = make(room)
    ex.step(room.observe())
    t = room.t
    for k in range(1, 40):
        cmd = ex.step(None, now=t + 0.2 * k)
    assert ex.outcome == Outcome.SENSOR_TIMEOUT and cmd.kind == CommandKind.STOP


# --------------------------------------------------------------------------- interruptions during approach
def _interrupt_during_approach(kind):
    room = restaurant(start=Pose2D(5.0, 3.6, 0.0))  # table 3 readable -> approach immediately
    ex = make(room, ocr_range=6.0)
    log = {"start": None}

    def hooks(t, room, ex):
        if log["start"] is None and ex.state == State.APPROACH and t > 0.5:
            log["start"] = t
        on = log["start"] is not None and log["start"] <= t < log["start"] + 2.0
        if kind == "camera":
            room.camera_on = not on
        else:
            room.pose_status = LocalizationStatus.LOST if on else LocalizationStatus.OK
            room.pose_sigma = 0.8 if on else 0.03

    stop, cmds, _ = run(ex, room, hooks=hooks, max_s=120)
    return room, ex, log


def test_camera_dropout_during_approach_resumes_and_delivers():
    """Regression: resuming APPROACH used to refresh the interrupt's HOLD forever (found in the
    K1 MuJoCo diagnostic trial, where a between-frames tick triggered SENSOR_WAIT)."""
    room, ex, log = _interrupt_during_approach("camera")
    assert log["start"] is not None
    assert any("re-entering approach" in e.msg for e in ex.events)
    assert_delivered_at(room, ex, 13)


def test_localization_loss_during_approach_resumes_and_delivers():
    room, ex, log = _interrupt_during_approach("pose")
    assert log["start"] is not None and any("relocalized" in e.msg for e in ex.events)
    assert_delivered_at(room, ex, 13)
