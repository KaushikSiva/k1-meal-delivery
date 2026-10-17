"""SOFTWARE TESTS on a synthetic fixture. Not simulator or robot performance evidence."""

import numpy as np

from autonomy.contracts import CommandKind, DeliveryTask, Outcome, Pose2D, Region
from autonomy.executive import DeliveryExecutive, ExecutiveConfig, State
from autonomy.grounding import parse_instruction
from fake_world import fixture_detector_2d, restaurant, run

REGIONS = [Region("dining_right", (7.5, 4.0), 2.5, ("dining",)), Region("window", (9.0, 4.0), 1.0, ("window",))]


def make(room, text="deliver the pizza and drink to table 3", ocr_range=2.0, cfg=None, **kw):
    task = DeliveryTask(text, parse_instruction(text), issued_at=room.t, time_limit_s=kw.pop("time_limit_s", 400))
    return DeliveryExecutive(task, room.grid(), fixture_detector_2d(room, ocr_range), REGIONS, cfg, **kw)


def edge_distance(room, seg_id):
    b = next(b for b in room.boxes if b.seg_id == seg_id)
    p = room.true_pose.xy()
    return float(np.linalg.norm(np.clip(p, b.lo[:2], b.hi[:2]) - p))


def assert_delivered_at(room, ex, table_seg_id):
    assert ex.outcome == Outcome.DELIVERED, [e.msg for e in ex.events]
    d = edge_distance(room, table_seg_id)
    assert 0.3 <= d <= 0.9, d
    others = [b.seg_id for b in room.boxes if b.label == "table" and b.seg_id != table_seg_id]
    assert all(edge_distance(room, o) > 1.0 for o in others)


def test_never_seen_destination_is_searched_verified_and_reached():
    room = restaurant()  # table 3 is behind the partition; no table visible at start
    ex = make(room)
    stop, cmds, ctrl = run(ex, room)
    assert_delivered_at(room, ex, 13)
    states = [c.state for c in cmds]
    assert State.SEARCH.value in states and State.FINAL_APPROACH.value in states
    # Other tables were seen/read and rejected along the way, never approached for final stop.
    assert ctrl.max_speed_seen <= ExecutiveConfig().approach_speed + 1e-6
