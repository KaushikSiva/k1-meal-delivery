"""Persistent, timestamped scene memory (map frame).

- Data association by tracker id, else nearest same-label within a Mahalanobis-ish gate.
- Confidence: noisy-OR on sightings, exponential time decay, and *negative evidence*
  (an object that should be visible from the current estimated camera pose, but isn't
  detected, loses confidence). Negative evidence is skipped while localization is not OK,
  otherwise a bad pose estimate would erase correct memories.
- Attributes (e.g. table_number) are fused per value with noisy-OR.
- Every object keeps first/last seen time and provenance; summaries are JSON-friendly.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

from autonomy.contracts import Detection, LocalizationStatus, Observation, Provenance
from perception.geometry import visible_mask


@dataclass
class TrackedObject:
    key: str
    label: str
    position: np.ndarray
    position_var: float  # scalar xy variance (m^2)
    confidence: float
    first_seen: float
    last_seen: float
    n_sightings: int = 1
    track_id: str | None = None
    attributes: dict[str, dict[str, float]] = field(default_factory=dict)  # name -> {value: conf}
    provenance: set[Provenance] = field(default_factory=set)
    extent: np.ndarray | None = None
    n_misses: int = 0
    # Union of observed xy footprints (partial views of large objects have shifting centroids,
    # so association/merging also uses footprint overlap, not only centroid distance).
    lo: np.ndarray | None = None
    hi: np.ndarray | None = None

    def grow(self, det: Detection) -> None:
        half = (np.asarray(det.extent[:2], float) / 2) if det.extent is not None else np.zeros(2)
        lo, hi = det.position[:2] - half, det.position[:2] + half
        self.lo = lo.copy() if self.lo is None else np.minimum(self.lo, lo)
        self.hi = hi.copy() if self.hi is None else np.maximum(self.hi, hi)

    def attribute(self, name: str) -> tuple[str | None, float]:
        vals = self.attributes.get(name)
        if not vals:
            return None, 0.0
        v = max(vals, key=vals.get)
        return v, vals[v]

    def age(self, now: float) -> float:
        return now - self.last_seen


def _footprint(extent) -> float:
    """Diagonal of the observed xy extent; partial views of large objects shift the centroid."""
    return 0.0 if extent is None else float(np.hypot(extent[0], extent[1]))


class SceneMemory:
    def __init__(
        self,
        gate_m: float = 0.5,
        half_life_s: float = 300.0,
        miss_factor: float = 0.6,
        forget_below: float = 0.03,
        max_range: float = 5.0,
    ):
        self.gate_m = gate_m
        self.half_life_s = half_life_s
        self.miss_factor = miss_factor
        self.forget_below = forget_below
        self.max_range = max_range
        self.objects: dict[str, TrackedObject] = {}
        self.aliases: dict[str, str] = {}  # merged-away key -> surviving key
        self.footprint_margin = 0.15
        self._ids = itertools.count()
        self.now = 0.0

    # ------------------------------------------------------------------ update
    def update(self, obs: Observation, detections: list[Detection]) -> None:
        self._decay_to(obs.timestamp)
        matched: set[str] = set()
        for det in detections:
            key = self._associate(det, matched)
            var = float(np.mean(np.diag(det.position_cov)[:2]))
            if key is None:
                key = f"{det.label}#{next(self._ids)}"
                self.objects[key] = TrackedObject(
                    key=key, label=det.label, position=np.asarray(det.position, float).copy(), position_var=var,
                    confidence=det.confidence * 0.7, first_seen=det.timestamp, last_seen=det.timestamp,
                    track_id=det.track_id, provenance={det.provenance}, extent=det.extent,
                )
                self._fuse_attributes(self.objects[key], det)
                self.objects[key].grow(det)
            else:
                m = self.objects[key]
                # Kalman-style scalar fusion of position.
                k = m.position_var / (m.position_var + var + 1e-9)
                m.position = m.position + k * (np.asarray(det.position, float) - m.position)
                m.position_var = (1 - k) * m.position_var
                m.confidence = 1 - (1 - m.confidence) * (1 - det.confidence * 0.7)
                m.last_seen = det.timestamp
                m.n_sightings += 1
                m.n_misses = 0
                m.provenance.add(det.provenance)
                m.track_id = det.track_id or m.track_id
                if det.extent is not None:
                    m.extent = det.extent if m.extent is None else np.maximum(m.extent, det.extent)
                self._fuse_attributes(m, det)
                m.grow(det)
            matched.add(key)
        self._negative_evidence(obs, matched)
        self._merge_overlapping()
        self._forget()

    # ------------------------------------------------------------------ queries
    def query(self, label: str, min_confidence: float = 0.0) -> list[TrackedObject]:
        return sorted(
            (m for m in self.objects.values() if m.label == label and m.confidence >= min_confidence),
            key=lambda m: -m.confidence,
        )

    def get(self, key: str) -> TrackedObject | None:
        seen = set()
        while key in self.aliases and key not in seen:  # follow merges
            seen.add(key)
            key = self.aliases[key]
        return self.objects.get(key)

    def summary(self) -> list[dict]:
        return [
            {
                "key": m.key, "label": m.label, "xyz": [round(float(v), 3) for v in m.position],
                "sigma_xy": round(float(np.sqrt(m.position_var)), 3), "conf": round(m.confidence, 3),
                "age_s": round(m.age(self.now), 1), "n_seen": m.n_sightings,
                "attributes": {a: m.attribute(a)[0] for a in m.attributes},
                "provenance": sorted(p.value for p in m.provenance),
            }
            for m in sorted(self.objects.values(), key=lambda m: m.key)
        ]

    # ------------------------------------------------------------------ internals
    def _fuse_attributes(self, m: TrackedObject, det: Detection) -> None:
        for name, (value, conf) in det.attributes.items():
            vals = m.attributes.setdefault(name, {})
            vals[value] = 1 - (1 - vals.get(value, 0.0)) * (1 - conf)

    def _associate(self, det: Detection, exclude: set[str]) -> str | None:
        if det.track_id is not None:
            for m in self.objects.values():
                if m.track_id == det.track_id and m.key not in exclude:
                    if np.linalg.norm(m.position[:2] - det.position[:2]) < 3 * self.gate_m:
                        return m.key
        best, best_d = None, np.inf
        probe = TrackedObject("_", det.label, det.position, 0, 0, 0, 0)
        probe.grow(det)
        for m in self.objects.values():
            if m.key in exclude or m.label != det.label or self._attributes_conflict(m, det):
                continue
            if self._overlap(m, probe):
                d = float(np.linalg.norm(m.position[:2] - det.position[:2]))
                if d < best_d:
                    best, best_d = m.key, d
                continue
            gate = max(self.gate_m, 2.5 * np.sqrt(m.position_var + det.position_cov[0, 0]),
                       0.8 * _footprint(m.extent), 0.8 * _footprint(det.extent))
            d = float(np.linalg.norm(m.position[:2] - det.position[:2]))
            if d < gate and d < best_d:
                best, best_d = m.key, d
        return best

    def _overlap(self, a: TrackedObject, b: TrackedObject) -> bool:
        if a.lo is None or b.lo is None:
            return False
        m = self.footprint_margin
        return bool(np.all(a.lo - m <= b.hi) and np.all(b.lo - m <= a.hi))

    def _merge_overlapping(self) -> None:
        objs = sorted(self.objects.values(), key=lambda o: (o.first_seen, o.key))
        for i, a in enumerate(objs):
            if a.key not in self.objects:
                continue
            for b in objs[i + 1:]:
                if b.key not in self.objects or a.label != b.label or not self._overlap(a, b):
                    continue
                if any(self._conflict_values(a, b, n) for n in set(a.attributes) & set(b.attributes)):
                    continue
                w_a, w_b = a.n_sightings, b.n_sightings
                a.position = (w_a * a.position + w_b * b.position) / (w_a + w_b)
                a.confidence = 1 - (1 - a.confidence) * (1 - b.confidence)
                a.first_seen, a.last_seen = min(a.first_seen, b.first_seen), max(a.last_seen, b.last_seen)
                a.n_sightings += b.n_sightings
                a.provenance |= b.provenance
                a.lo, a.hi = np.minimum(a.lo, b.lo), np.maximum(a.hi, b.hi)
                for name, vals in b.attributes.items():
                    tgt = a.attributes.setdefault(name, {})
                    for v, c in vals.items():
                        tgt[v] = 1 - (1 - tgt.get(v, 0.0)) * (1 - c)
                self.aliases[b.key] = a.key
                del self.objects[b.key]

    @staticmethod
    def _conflict_values(a: TrackedObject, b: TrackedObject, name: str, conf: float = 0.6) -> bool:
        va, ca = a.attribute(name)
        vb, cb = b.attribute(name)
        return va is not None and vb is not None and va != vb and ca >= conf and cb >= conf

    @staticmethod
    def _attributes_conflict(m: TrackedObject, det: Detection, conf: float = 0.6) -> bool:
        for name, (value, c) in det.attributes.items():
            have, hc = m.attribute(name)
            if have is not None and have != value and c >= conf and hc >= conf:
                return True
        return False

    def _decay_to(self, t: float) -> None:
        dt = max(0.0, t - self.now)
        self.now = max(self.now, t)
        if dt > 0 and self.half_life_s > 0:
            f = 0.5 ** (dt / self.half_life_s)
            for m in self.objects.values():
                m.confidence *= f

    def _negative_evidence(self, obs: Observation, matched: set[str]) -> None:
        T = obs.T_map_camera()
        if T is None or obs.camera.depth is None or obs.pose.status != LocalizationStatus.OK:
            return
        cands = [m for m in self.objects.values() if m.key not in matched]
        if not cands:
            return
        vis = visible_mask(np.array([m.position for m in cands]), obs.camera.intrinsics, T, obs.camera.depth,
                           max_range=self.max_range)
        for m, v in zip(cands, vis):
            if v:
                m.confidence *= self.miss_factor
                m.n_misses += 1

    def _forget(self) -> None:
        for k in [k for k, m in self.objects.items() if m.confidence < self.forget_below]:
            del self.objects[k]
