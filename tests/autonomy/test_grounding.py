"""SOFTWARE TESTS: instruction parsing and candidate verdicts."""

import numpy as np

from autonomy.contracts import Detection, Observation, Provenance
from autonomy.grounding import Verdict, match_candidates, parse_instruction
from memory import SceneMemory


def test_parse_variants():
    s = parse_instruction("Deliver the pizza box and the drink to table 3")
    assert s.category == "table" and s.attr() == {"table_number": "3"}
    assert parse_instruction("take it to table number five").attr() == {"table_number": "5"}
    s = parse_instruction("bring this to the person in the red shirt")
    assert s.category == "person" and s.attr() == {"color": "red"}
    s = parse_instruction("please take the tray to the table by the window")
    assert s.category == "table" and s.attr() == {} and s.region_hint == "window"
    assert parse_instruction("drop it at the counter").category == "counter"


def _det(label, xy, attrs=None, t=0.0):
    return Detection(label, np.array([*xy, 0.5]), np.eye(3) * 0.01, 0.9, t, Provenance.ESTIMATED,
                     attributes=attrs or {})


def test_verdicts():
    mem = SceneMemory()
    obs = Observation(0.0, None, None)
    mem.update(obs, [_det("table", (1, 1), {"table_number": ("3", 0.9)}),
                     _det("table", (5, 1), {"table_number": ("2", 0.9)}),
                     _det("table", (9, 1))])
    spec = parse_instruction("to table 3")
    v = {tuple(np.round(c.obj.position[:2]).astype(int)): c.verdict for c in match_candidates(spec, mem)}
    assert v == {(1, 1): Verdict.CONFIRMED, (5, 1): Verdict.REJECTED, (9, 1): Verdict.POSSIBLE}


def test_identity_merge_uses_only_identity_attributes():
    """Codex review 20:50Z: shared appearance (color) must not merge two nearby tables; a shared
    table number within 1.2 m still merges (same physical table seen from two sides); duplicate
    numbers farther apart stay separate (-> ambiguity)."""
    mem = SceneMemory()
    obs = Observation(0.0, None, None)
    # two red tables 0.9 m apart, small partial footprints (no overlap)
    mem.update(obs, [_det("table", (1.0, 1.0), {"color": ("red", 0.9)}),
                     _det("table", (1.9, 1.0), {"color": ("red", 0.9)})])
    assert len(mem.query("table")) == 2
    # same table number seen from two sides 0.6 m apart -> one track
    mem2 = SceneMemory()
    mem2.update(obs, [_det("table", (5.0, 1.0), {"table_number": ("3", 0.9)})])
    mem2.update(Observation(1.0, None, None), [_det("table", (5.6, 1.0), {"table_number": ("3", 0.9)}, t=1.0)])
    assert len(mem2.query("table")) == 1
    # duplicate number far apart -> two tracks (executive reports AMBIGUOUS)
    mem3 = SceneMemory()
    mem3.update(obs, [_det("table", (1.0, 1.0), {"table_number": ("3", 0.9)}),
                      _det("table", (5.0, 1.0), {"table_number": ("3", 0.9)})])
    assert len(mem3.query("table")) == 2
