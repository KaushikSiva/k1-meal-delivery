"""Instruction -> DestinationSpec, and DestinationSpec x SceneMemory -> candidate verdicts.

Grounding is *visual*: the instruction says what the destination looks like ("table 3",
"the person in the red shirt", "the table by the window"); the destination's location is
only ever known from detections in scene memory. Region hints bias search; they never
confirm a destination.

Keyword parser for now. An LLM/VLM parser can replace `parse_instruction` as long as it
returns the same DestinationSpec.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from memory import SceneMemory, TrackedObject
from .contracts import DestinationSpec

CATEGORY_WORDS = {
    "table": ["table", "booth", "desk"],
    "person": ["person", "guest", "customer", "man", "woman", "me", "him", "her", "them"],
    "counter": ["counter", "pass", "bar"],
}
COLORS = ["red", "blue", "green", "yellow", "black", "white", "orange", "purple", "pink", "gray", "grey", "brown"]
REGION_WORDS = ["window", "door", "entrance", "kitchen", "corner", "patio", "stage"]
NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
                "seven": "7", "eight": "8", "nine": "9", "ten": "10"}


class ParseError(ValueError):
    pass


def parse_instruction(text: str) -> DestinationSpec:
    t = text.lower()
    # Strip the payload phrase so "bring the pizza and drink to ..." doesn't confuse matching.
    m = re.search(r"\b(?:to|for|at)\b\s+(.*)$", t)
    dest_text = m.group(1) if m else t

    category = None
    first = len(dest_text) + 1
    for cat, words in CATEGORY_WORDS.items():
        for w in words:
            mm = re.search(rf"\b{re.escape(w)}\b", dest_text)
            if mm and mm.start() < first:
                category, first = cat, mm.start()
    if category is None:
        raise ParseError(f"no destination category found in: {text!r}")

    attrs: list[tuple[str, str]] = []
    if category == "table":
        nm = re.search(r"\b(?:table|booth|desk)\s*(?:number|no\.?|#)?\s*(\d+|" + "|".join(NUMBER_WORDS) + r")\b",
                       dest_text)
        if nm:
            attrs.append(("table_number", NUMBER_WORDS.get(nm.group(1), nm.group(1))))
    for c in COLORS:
        if re.search(rf"\b{c}\b", dest_text):
            attrs.append(("color", "gray" if c == "grey" else c))
            break
    hint = next((w for w in REGION_WORDS if re.search(rf"\b{w}\b", dest_text)), None)
    return DestinationSpec(category=category, attributes=tuple(attrs), region_hint=hint)


class Verdict(str, Enum):
    CONFIRMED = "confirmed"  # category + every required attribute observed and matching
    POSSIBLE = "possible"  # category matches, some required attribute not yet observed
    REJECTED = "rejected"  # a required attribute was observed with a different value


@dataclass
class Candidate:
    obj: TrackedObject
    verdict: Verdict
    score: float  # confidence product, for ranking
    missing: tuple[str, ...] = ()


def match_candidates(
    spec: DestinationSpec, memory: SceneMemory, min_conf: float = 0.25, attr_conf: float = 0.6
) -> list[Candidate]:
    required = spec.attr()
    out = []
    for obj in memory.query(spec.category, min_conf):
        verdict, score, missing = Verdict.CONFIRMED, obj.confidence, []
        for name, want in required.items():
            got, conf = obj.attribute(name)
            want_conf = obj.attributes.get(name, {}).get(want, 0.0)
            if got is not None and got != want and conf >= attr_conf and want_conf < attr_conf:
                verdict = Verdict.REJECTED
                break
            if want_conf >= attr_conf:
                score *= want_conf
            else:
                missing.append(name)
        if verdict != Verdict.REJECTED and missing:
            verdict = Verdict.POSSIBLE
            score *= 0.3
        out.append(Candidate(obj, verdict, score, tuple(missing)))
    return sorted(out, key=lambda c: -c.score)
