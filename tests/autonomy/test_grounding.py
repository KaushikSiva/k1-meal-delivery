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
