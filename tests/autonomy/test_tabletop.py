"""SOFTWARE TESTS: unmarked table/counter detection from depth geometry (no masks, labels, markers)."""

import numpy as np

from autonomy.contracts import DeliveryTask, Outcome, Pose2D, Provenance
from autonomy.executive import DeliveryExecutive
from autonomy.grounding import parse_instruction
from fake_world import Box, FakeRoom, restaurant, run
from perception.tabletop import CombinedDetector, TabletopDetector


def _matches(d, room, z_tol=0.08, xy_tol=0.15):
    return any(b.label == d.label and np.all(d.position[:2] >= b.lo[:2] - xy_tol)
               and np.all(d.position[:2] <= b.hi[:2] + xy_tol) and abs(d.position[2] - b.hi[2]) < z_tol
               for b in room.boxes)


def test_random_views_have_no_false_detections_and_find_tables():
    rng = np.random.default_rng(0)
    true_dets = views = 0
    for _ in range(60):
        room = restaurant(start=Pose2D(rng.uniform(4.5, 8), rng.uniform(0.5, 7.5), rng.uniform(-np.pi, np.pi)))
        g = room.grid()
        if g.data[g.world_to_cell(room.true_pose.xy())]:
            continue
        views += 1
        for d in TabletopDetector().detect(room.observe()):
            assert _matches(d, room), f"false detection {d.label} at {d.position} from {room.true_pose}"
            true_dets += 1
    assert views > 40 and true_dets >= 30


def test_walls_chairs_and_people_are_not_tables():
    room = FakeRoom([
        Box(1, "wall", np.array([3.0, 0.0, 0.0]), np.array([3.2, 4.0, 2.0])),
        Box(2, "chair", np.array([2.0, 1.6, 0.0]), np.array([2.4, 2.0, 0.45])),
        Box(3, "person", np.array([2.2, 2.6, 0.0]), np.array([2.5, 2.9, 1.7])),
    ], bounds=(0, 0, 6, 4), start=Pose2D(0.8, 2.0, 0.0))
    assert TabletopDetector().detect(room.observe()) == []


def test_mask_free_perception_loop_with_MOCKED_estimator_interface_check():
    """INTERFACE CHECK ONLY, not deployable localization evidence. No masks/labels/placards are
    used and the executive runs with deployable=True (guard active), BUT the pose is the fixture's
    ground truth relabeled ESTIMATED as a mock estimator (noise/bias does not launder GT, per the
    Q1 decision). It shows that the mask-free perception -> memory -> executive path works end to
    end; real deployable localization (odometry/VSLAM from sensor history) is still required."""
    room = FakeRoom([
        Box(1, "wall", np.array([4.0, 0.0, 0.0]), np.array([4.2, 3.0, 2.0])),
        Box(2, "table", np.array([6.5, 1.0, 0.0]), np.array([7.4, 1.8, 0.74])),
    ], bounds=(0, 0, 8, 5), start=Pose2D(1.0, 1.0, 0.0))
    room.emit_segmentation = False
    room.pose_provenance = Provenance.ESTIMATED  # MOCK: truth relabeled to exercise the deployable path
    text = "deliver the pizza and drink to the table"
    task = DeliveryTask(text, parse_instruction(text), 0.0, 300)
    det = CombinedDetector(TabletopDetector())
    ex = DeliveryExecutive(task, room.grid(), det, deployable=True)
    run(ex, room)
    assert ex.outcome == Outcome.DELIVERED, [e.msg for e in ex.events]
    t = room.boxes[1]
    p = room.true_pose.xy()
    assert 0.2 <= np.linalg.norm(np.clip(p, t.lo[:2], t.hi[:2]) - p) <= 0.9
    assert ex.memory.objects and all(o.provenance == {Provenance.ESTIMATED} for o in ex.memory.objects.values())


# ----------------------------------------------------------------------------- K1 head-camera renders
import pytest  # noqa: E402


@pytest.mark.parametrize("dist", [1.0, 1.5, 2.0])
def test_k1_render_table_geometry_and_placard_fuse_into_confirmed_table_3(tmp_path, dist):
    """Official K1 model head camera (MuJoCo, via Codex's sim adapter; pose privileged, posed robot).
    Table center is at x = dist + 0.5 (0.8 x 1.0 m top at 0.75 m). Placard = restricted diagnostic."""
    from test_placard import _render_k1_view

    from autonomy.grounding import Verdict, match_candidates
    from memory import SceneMemory
    from perception.detectors import BoxLifter
    from perception.placard import PlacardReader

    obs = _render_k1_view(tmp_path, 3, dist)
    tables = TabletopDetector().detect(obs)
    assert len(tables) == 1
    t = tables[0]
    assert np.linalg.norm(t.position[:2] - [dist + 0.5, 0.0]) < 0.1 and abs(t.position[2] - 0.75) < 0.02
    assert np.allclose(t.extent[:2], [0.8, 1.0], atol=0.1)
    mem = SceneMemory()
    mem.update(obs, tables + BoxLifter(PlacardReader()).detect(obs))
    cands = match_candidates(parse_instruction("deliver to table 3"), mem)
    assert len(mem.objects) == 1 and [c.verdict for c in cands] == [Verdict.CONFIRMED]
    # Codex's adapter pose/extrinsics are simulator truth: everything derived is privileged.
    assert all(d.provenance == Provenance.SIM_PRIVILEGED for d in tables)
    assert Provenance.SIM_PRIVILEGED in next(iter(mem.objects.values())).provenance


def test_taint_propagates_from_privileged_pose_or_camera_to_detections_and_memory():
    """Regression (Codex review 19:53Z): measured RGB-D + privileged pose => privileged detections."""
    from memory import SceneMemory
    from perception.detectors import BoxLifter
    from perception.placard import PlacardReader

    room = restaurant(start=Pose2D(4.6, 1.4, 0.0))
    room.emit_segmentation = False
    obs = room.observe()
    assert obs.pose.provenance == Provenance.SIM_PRIVILEGED and obs.camera.provenance == Provenance.MEASURED
    dets = TabletopDetector().detect(obs)
    assert dets and all(d.provenance == Provenance.SIM_PRIVILEGED for d in dets)
    mem = SceneMemory()
    mem.update(obs, dets)
    assert all(Provenance.SIM_PRIVILEGED in o.provenance for o in mem.objects.values())
    # privileged camera frame (e.g. GT extrinsics) taints too, even with an ESTIMATED pose
    room.pose_provenance = Provenance.ESTIMATED
    obs = room.observe()
    assert all(d.provenance == Provenance.ESTIMATED for d in TabletopDetector().detect(obs))
    obs.camera.provenance = Provenance.SIM_PRIVILEGED
    assert all(d.provenance == Provenance.SIM_PRIVILEGED for d in TabletopDetector().detect(obs))
    rgb = np.zeros((obs.camera.intrinsics.height, obs.camera.intrinsics.width, 3), np.uint8)
    from perception.placard import make_placard
    rgb[10:50, 20:60] = make_placard(3)[::3, ::3][:40, :40]
    obs.camera.rgb = rgb
    lifted = BoxLifter(PlacardReader()).detect(obs)
    assert lifted and all(d.provenance == Provenance.SIM_PRIVILEGED for d in lifted)


# ----------------------------------------------------------------------------- wall-corner false table
def test_codex_sensor_nav_capture_frame_48_has_no_false_table():
    """Regression (Codex sensor-nav trial 21:35Z, real MuJoCo K1 head-camera capture): the real
    tabletop's height peak is global, so slices of two walls meeting in a corner at that height
    formed an L-shaped 'table'. A local check (points 0.35-1.0 m above the cluster's own cells)
    rejects wall slices but keeps tops. (A low-res fixture could not reproduce the corner, so the
    real capture is the regression; it skips if the git-ignored npz is absent.)"""
    from pathlib import Path
    from autonomy.contracts import CameraFrame, CameraIntrinsics, Observation, PoseEstimate

    f = Path(__file__).resolve().parents[2] / "experiments/codex-20261017T2141-sensor-navigation-capture/rgbd-0048.npz"
    if not f.exists():
        pytest.skip("Codex capture not present (npz is git-ignored)")
    z = np.load(f, allow_pickle=True)
    depth = z["depth"].astype(np.float32)
    H, W = depth.shape
    t = float(z["timestamp"])
    obs = Observation(t, CameraFrame(t, CameraIntrinsics.from_fovy(58, W, H), z["T_base_camera"], rgb=z["rgb"],
                                     depth=depth),
                      PoseEstimate(Pose2D(*map(float, z["pose"])), z["cov"], t, "replay", Provenance.ESTIMATED))
    dets = TabletopDetector().detect(obs)
    assert len(dets) == 1 and np.hypot(dets[0].position[0] - 4.0, dets[0].position[1]) < 0.2
    # discriminating: without the local above-check the wall corner (x 7, y -3) is reported as a table
    old = TabletopDetector(max_above_ratio=np.inf).detect(obs)
    assert any(np.hypot(d.position[0] - 6.53, d.position[1] + 2.53) < 0.3 for d in old)
