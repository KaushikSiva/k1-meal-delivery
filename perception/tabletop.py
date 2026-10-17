"""Unmarked table / counter detection from depth geometry (deployable: depth + estimated pose only).

Horizontal surfaces are found without any appearance model:
  1. back-project depth pixels to the map frame (estimated camera pose);
  2. height histogram per class band; a horizontal surface is a *prominent* peak (>= min_prominence x
     the density 4-10 cm above it: nothing sits just above a tabletop). Vertical faces (walls, people, table sides) have no prominence;
  3. peak points are clustered in xy; thin strips (a face sliced at the peak height) are rejected;
  4. table-sized clusters become detections (ESTIMATED).

Height bands are priors (dining tables ~0.70-0.78 m, counters ~0.9-1.1 m), not measurements of a
specific café; set them from the scene/venue survey. Chairs (~0.45 m) and the floor fall outside.
Limitations: a surface needs the camera above it (K1 head camera ~0.9 m sees dining tabletops at a
grazing angle, so range is limited); cluttered tabletops reduce flat cells; adjacent tables touching
in the image may merge.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from autonomy.contracts import Detection, Observation, Provenance
from .detectors import derived_provenance, point_covariance, worst_provenance
from .geometry import backproject, valid_depth
from .placard import components


@dataclass(frozen=True)
class SurfaceClass:
    label: str
    z_lo: float
    z_hi: float
    min_side: float  # m
    max_side: float  # m


DEFAULT_CLASSES = (
    SurfaceClass("table", 0.60, 0.85, 0.35, 2.2),
    SurfaceClass("counter", 0.86, 1.10, 0.5, 5.0),
)


class TabletopDetector:
    provenance = Provenance.ESTIMATED

    def __init__(self, classes=DEFAULT_CLASSES, cell: float = 0.1, stride: int = 1, max_range: float = 5.0,
                 z_bin: float = 0.01, z_tol: float = 0.02, min_peak_pts: int = 25, min_cells: int = 3,
                 min_short_side: float = 0.2, min_prominence: float = 4.0):
        self.classes = classes
        self.cell, self.stride, self.max_range = cell, stride, max_range
        self.z_bin, self.z_tol, self.min_peak_pts = z_bin, z_tol, min_peak_pts
        self.min_cells, self.min_short_side = min_cells, min_short_side
        self.min_prominence = min_prominence

    def detect(self, obs: Observation) -> list[Detection]:
        cam = obs.camera
        T = obs.T_map_camera()
        if cam is None or cam.depth is None or T is None:
            return []
        d = cam.depth[::self.stride, ::self.stride]
        vs, us = np.nonzero(valid_depth(d, self.max_range))
        if len(vs) == 0:
            return []
        z = d[vs, us].astype(float)
        pts = backproject(us * float(self.stride), vs * float(self.stride), z, cam.intrinsics, T)
        prov = derived_provenance(obs)
        out = []
        for cls in self.classes:
            band = pts[(pts[:, 2] >= cls.z_lo) & (pts[:, 2] <= cls.z_hi)]
            band_all = pts[(pts[:, 2] >= cls.z_lo) & (pts[:, 2] <= cls.z_hi + 0.12)]
            if len(band) < self.min_peak_pts:
                continue
            # 1. height peaks: a horizontal surface piles points at one height; vertical faces don't
            edges = np.arange(cls.z_lo, cls.z_hi + self.z_bin, self.z_bin)
            hist, _ = np.histogram(band[:, 2], edges)
            floor_level = self.min_peak_pts  # prominence (below) does the discrimination
            def prominence(i):
                # density 4-10 cm ABOVE: nothing sits just above a tabletop, but a wall/person/face
                # continues upward. (Below is unusable: the table's own front face fills it at
                # grazing view angles.)
                ring = hist[i + 4:i + 11]
                if len(ring) < 3:  # band edge: extend the histogram upward instead
                    ring = np.histogram(band_all[:, 2], np.arange(edges[i] + 0.04, edges[i] + 0.11, self.z_bin))[0]
                return hist[i] / (float(ring.mean()) + 1.0) if len(ring) else np.inf

            peaks = [i for i in range(len(hist)) if hist[i] >= floor_level
                     and hist[i] == hist[max(0, i - 2):i + 3].max() and prominence(i) >= self.min_prominence]
            for i in peaks:
                zc = 0.5 * (edges[i] + edges[i + 1])
                q = band[np.abs(band[:, 2] - zc) <= self.z_tol]
                # 2. cluster the surface points in xy
                ox, oy = q[:, 0].min(), q[:, 1].min()
                ci = np.floor((q[:, 0] - ox) / self.cell).astype(int)
                ri = np.floor((q[:, 1] - oy) / self.cell).astype(int)
                grid = np.zeros((ri.max() + 1, ci.max() + 1), bool)
                grid[ri, ci] = True
                for rr, cc in components(grid, self.min_cells):
                    sx = (cc.max() - cc.min() + 1) * self.cell
                    sy = (rr.max() - rr.min() + 1) * self.cell
                    if max(sx, sy) < cls.min_side or max(sx, sy) > cls.max_side or min(sx, sy) < self.min_short_side:
                        continue  # thin strips = a vertical face sliced at this height
                    cellset = set(zip(rr.tolist(), cc.tolist()))
                    member = np.array([(r, c) in cellset for r, c in zip(ri, ci)])
                    sp = q[member]
                    lo, hi = sp[:, :2].min(0), sp[:, :2].max(0)
                    if min(hi - lo) < self.min_short_side:
                        continue  # measured (not cell-padded) extent is a thin strip
                    conf = float(np.clip(len(sp) / (len(sp) + 60.0), 0.3, 0.95))
                    rng = float(np.linalg.norm(sp.mean(0) - T[:3, 3]))
                    out.append(Detection(
                        label=cls.label, position=np.array([*(lo + hi) / 2, float(np.median(sp[:, 2]))]),
                        position_cov=point_covariance(obs, rng), confidence=conf, timestamp=cam.timestamp,
                        provenance=prov, extent=np.array([*(hi - lo), 0.02]),
                    ))
        return out


class CombinedDetector:
    """Run several detectors; provenance is the least trustworthy of its parts."""

    def __init__(self, *detectors):
        self.detectors = detectors
        self.provenance = worst_provenance(*(d.provenance for d in detectors))

    def detect(self, obs: Observation) -> list[Detection]:
        return [det for d in self.detectors for det in d.detect(obs)]
