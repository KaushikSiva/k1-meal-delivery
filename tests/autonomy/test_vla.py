"""SOFTWARE TESTS of the VLA interface with fake proposal sources. No model is trained or run."""

import json

import numpy as np
import pytest

from autonomy.contracts import CommandKind, LocalizationStatus, Outcome
from autonomy.executive import State
from fake_world import KinematicController, restaurant
from test_nominal import assert_delivered_at, make
from vla.action_space import ACTION_DIM, LocalSubgoal, decode, encode
from vla.adapter import BoundedActionAdapter, VLAProposal
from vla.inputs import STATE_DIM, build_inputs
from vla.recorder import DemoRecorder, label_from_command
from vla.remote import RemoteVLAClient


def test_action_roundtrip_and_validation():
    g = LocalSubgoal(0.8, -0.3, 0.4, 0.2, False)
    g2 = decode(encode(g))
    assert np.allclose([g.dx, g.dy, g.dyaw, g.speed], [g2.dx, g2.dy, g2.dyaw, g2.speed], atol=1e-6) and not g2.hold
    with pytest.raises(ValueError):
        decode(np.array([0, 0, np.nan, 0, 0]))
    with pytest.raises(ValueError):
        decode(np.zeros(3))
    big = decode(np.full(ACTION_DIM, 50.0))  # out-of-range values are clipped to bounds
    assert big.dx == pytest.approx(1.5) and big.speed == pytest.approx(0.35)


def closed_loop(room, ex, propose, adapter, hooks=None, max_s=400):
    ctrl = KinematicController(room)
    fb, cmds = None, []
    while room.t < max_s:
        if hooks:
            hooks(room.t, room, ex)
        obs = room.observe()
        exec_cmd = ex.step(obs, fb)
        cmd = adapter.select(ex, exec_cmd, obs, propose(obs, ex, exec_cmd))
        cmds.append(cmd)
        if cmd.kind == CommandKind.STOP:
            return cmds, ctrl
        fb = ctrl.step(cmd)
    raise AssertionError("no terminal command")


def test_teacher_imitating_vla_runs_through_adapter_and_delivers():
    room = restaurant()
    ex = make(room)
    adapter = BoundedActionAdapter()

    def teacher(obs, ex, exec_cmd):  # stands in for a perfectly-trained model
        return VLAProposal(label_from_command(exec_cmd, obs)[None], obs.timestamp, "teacher-replay")

    cmds, _ = closed_loop(room, ex, teacher, adapter)
    assert_delivered_at(room, ex, 13)
    assert any(c.selected_by == "vla" for c in cmds)
    assert all(c.selected_by == "executive" for c in cmds if c.state in ("final_approach", "settle"))


def test_random_vla_cannot_override_safety():
    room = restaurant()
    ex = make(room, time_limit_s=200)
    adapter = BoundedActionAdapter()
    rng = np.random.default_rng(0)
    log = []

    def hooks(t, room, ex):
        log.append((t, room.true_pose.xy().copy()))
        lost = 20.0 <= t < 30.0
        room.pose_status = LocalizationStatus.LOST if lost else LocalizationStatus.OK
        room.pose_sigma = 0.8 if lost else 0.03

    def rand(obs, ex, exec_cmd):
        a = rng.uniform(-1, 1, (1, ACTION_DIM))
        if rng.random() < 0.05:
            a[0, 0] = np.nan
        return VLAProposal(a, obs.timestamp, "random")

    cmds, ctrl = closed_loop(room, ex, rand, adapter, hooks)
    assert ex.outcome != Outcome.DELIVERED or ex.state == State.DONE  # completion only via executive
    assert ctrl.max_speed_seen <= 0.35 + 1e-6
    moved = max(np.linalg.norm(b - a) for (ta, a), (tb, b) in zip(log, log[1:]) if 20.6 <= ta and tb < 30.0)
    assert moved < 0.05
    reasons = {d.reason for d in adapter.decisions}
    assert any(r.startswith("invalid action") for r in reasons)
    assert any(r.startswith("executive-only state relocalize") for r in reasons)


def test_inputs_and_recorder(tmp_path):
    room = restaurant()
    ex = make(room)
    rec = DemoRecorder("fixture-ep0", {"source": "fixture", "privileged_inputs": ["fixture_detector_masks"]})
    fb = None
    ctrl = KinematicController(room)
    for _ in range(60):
        obs = room.observe()
        cmd = ex.step(obs, fb)
        inp = build_inputs(obs, ex)
        assert inp["observation.state"].shape == (STATE_DIM,) and "memory:" in inp["task"]
        rec.record(obs, ex, cmd)
        fb = ctrl.step(cmd)
    out = rec.finish(tmp_path, "truncated")
    d = np.load(out / "fixture-ep0.npz")
    assert d["action"].shape == (60, ACTION_DIM) and np.all(np.abs(d["action"]) <= 1)
    meta = json.loads((out / "fixture-ep0.meta.json").read_text())
    assert meta["provenance"]["privileged_inputs"]


def test_remote_client_failure_returns_none():
    c = RemoteVLAClient("http://127.0.0.1:9/act", timeout_s=0.2)
    assert c.propose({"task": "x", "observation.state": np.zeros(STATE_DIM), "timestamp": 0.0}) is None
    assert c.failures == 1
