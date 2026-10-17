"""SOFTWARE TESTS: live depth obstacle layer on the synthetic fixture."""

import numpy as np

from autonomy.contracts import LocalizationStatus, Pose2D
from fake_world import Box, restaurant
from navigation import Navigator
from navigation.depth_obstacles import DepthObstacleLayer


def _room_with_cart():
    room = restaurant(start=Pose2D(1.0, 2.0, 0.0))
    cart = Box(60, "cart", np.array([2.4, 1.6, 0.0]), np.array([2.9, 2.4, 0.9]), in_map=False)
    room.boxes.append(cart)
    return room, cart


def test_unmapped_obstacle_is_detected_and_planned_around():
    room, cart = _room_with_cart()
    grid = room.grid()
    nav = Navigator(grid)
    straight = nav.plan((1.0, 2.0), (3.6, 2.0))
    assert all(abs(p[1] - 2.0) < 0.05 for p in straight)  # prior map: straight through the cart
    layer = DepthObstacleLayer(grid)
    for _ in range(3):
        room.t += 0.2
        assert layer.update(room.observe())
    assert layer.occupied[grid.world_to_cell((2.45, 2.0))]
    assert not layer.occupied[grid.world_to_cell((1.8, 2.0))]  # open floor between robot and cart
    layer.apply_to(nav)
    path = nav.plan((1.0, 2.0), (3.6, 2.0))
    assert path is not None and max(abs(p[1] - 2.0) for p in path) > 0.6  # detours


def test_obstacle_clears_when_it_leaves():
    room, cart = _room_with_cart()
    layer = DepthObstacleLayer(room.grid())
    for _ in range(3):
        room.t += 0.2
        layer.update(room.observe())
    cell = room.grid().world_to_cell((2.45, 2.0))
    assert layer.occupied[cell]
    cart.visible = False
    for _ in range(10):
        room.t += 0.2
        layer.update(room.observe())
    assert not layer.occupied[cell]


def test_floor_is_not_an_obstacle_and_degraded_pose_is_ignored():
    room = restaurant(start=Pose2D(1.0, 2.0, 0.0))  # empty floor ahead up to the partition
    layer = DepthObstacleLayer(room.grid())
    room.t += 0.2
    layer.update(room.observe())
    g = room.grid()
    ys = slice(*sorted(g.world_to_cell((0, y))[0] for y in (1.5, 2.5)))
    xs = slice(*sorted(g.world_to_cell((x, 0))[1] for x in (1.4, 3.5)))
    assert not layer.occupied[ys, xs].any()
    room.pose_status = LocalizationStatus.DEGRADED
    room.t += 0.2
    assert not layer.update(room.observe()) and layer.frames_skipped == 1


def _cart_scenario(obstacle_layer):
    from fake_world import run
    from test_nominal import make

    room = restaurant(start=Pose2D(2.0, 6.0, np.deg2rad(-20)))
    room.boxes.append(Box(60, "cart", np.array([3.6, 4.5, 0.0]), np.array([4.6, 5.5, 0.9]), in_map=False))
    ex = make(room, ocr_range=10.0, obstacle_layer=obstacle_layer)
    run(ex, room)
    return room, ex


def test_closed_loop_avoids_unmapped_obstacle_without_bumping():
    from test_nominal import assert_delivered_at

    room, ex = _cart_scenario(obstacle_layer=True)
    assert_delivered_at(room, ex, 13)
    assert not any("blocked" in e.msg for e in ex.events)  # never touched the cart
    _, ex0 = _cart_scenario(obstacle_layer=False)  # ablation: prior map + contact feedback only
    assert any("blocked" in e.msg for e in ex0.events)


def test_obstacle_appearing_after_planning_triggers_replan_before_contact():
    """A cart is pushed into the corridor after the route was planned (fixture hook)."""
    from fake_world import run
    from test_nominal import assert_delivered_at, make

    room = restaurant(start=Pose2D(2.0, 6.0, np.deg2rad(-20)))
    cart = Box(60, "cart", np.array([4.6, 4.7, 0.0]), np.array([5.3, 5.6, 0.9]), in_map=False,
               visible=False, solid=False)
    room.boxes.append(cart)
    ex = make(room, ocr_range=10.0)
    state = {"planned_through": None}

    def hooks(t, room, ex):
        if cart.visible or ex.active is None or ex.active.path is None or ex.state.value != "approach":
            return
        pts = np.array(ex.active.path)
        seg = np.diff(pts, axis=0)
        rel = cart.center[:2] - pts[:-1]
        u = np.clip(np.einsum("ij,ij->i", rel, seg) / np.maximum(np.einsum("ij,ij->i", seg, seg), 1e-9), 0, 1)
        through = np.any(np.linalg.norm(pts[:-1] + u[:, None] * seg - cart.center[:2], axis=1) < 0.6)
        if through and room.true_pose.x < 3.8:
            state["planned_through"] = t
            cart.visible = cart.solid = True  # appears ahead of the robot, on the planned route

    run(ex, room, hooks=hooks)
    assert state["planned_through"] is not None, "fixture never placed the cart on the active route"
    assert any("observed obstacle" in e.msg for e in ex.events)
    assert not any("blocked" in e.msg for e in ex.events)
    assert_delivered_at(room, ex, 13)


def test_shortcut_paths_pass_the_same_check_used_for_revalidation():
    """Regression (found in the estimated-pose closed loop): planner line-of-sight rounding let
    shortcuts graze inflated corners that Navigator.path_is_free rejected -> endless replanning."""
    rng = np.random.default_rng(3)
    room = restaurant()
    nav = Navigator(room.grid())
    mask = np.zeros_like(nav.dynamic)
    for _ in range(25):  # random live obstacles
        r, c = rng.integers(5, mask.shape[0] - 5), rng.integers(5, mask.shape[1] - 5)
        mask[r - 1:r + 2, c - 1:c + 2] = True
    nav.set_dynamic_obstacles(mask)
    checked = 0
    for _ in range(300):
        s = (rng.uniform(0.5, 9.5), rng.uniform(0.5, 7.5))
        g = (rng.uniform(0.5, 9.5), rng.uniform(0.5, 7.5))
        path = nav.plan(s, g)
        if path is None or not nav.free[nav.grid.world_to_cell(s)]:
            continue
        checked += 1
        assert nav.path_is_free(path, path[0]), (s, g, path)  # executive call pattern: full path incl. start
        # every segment incl. the exact start and exact goal segments, sampled densely, no skip
        for a, b in zip(path, path[1:]):
            a, b = np.asarray(a), np.asarray(b)
            for t in np.linspace(0, 1, int(np.ceil(np.linalg.norm(b - a) / 0.01)) + 1):
                rc = nav.grid.world_to_cell(a + t * (b - a))
                if np.linalg.norm(a + t * (b - a) - np.asarray(path[0])) > 0.31:  # start may sit in a margin
                    assert nav.free[rc], (s, g, path, a + t * (b - a))
    assert checked > 20
