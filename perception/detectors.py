"""Detectors producing map-frame `Detection`s from an `Observation`.

Deployable path
    BoxLifter: takes 2D boxes from any image model (open-vocabulary detector, OCR for
    table numbers, ...) and lifts them to 3D with depth + the *estimated* camera pose.
    Output provenance = ESTIMATED.

Simulator-only paths (provenance = SIM_PRIVILEGED; rejected when deployable=True)
    SimSegmentationDetector: uses rendered instance masks. Useful to develop memory/search
        before a learned detector exists.
    GroundTruthDetector: reads object poses from obs.extra["gt_objects"]; diagnostics only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

import numpy as np

from autonomy.contracts import Detection, Observation, Provenance
from .geometry import backproject, project_points, valid_depth


_TRUST = {Provenance.MEASURED: 0, Provenance.OPERATOR: 1, Provenance.ESTIMATED: 1, Provenance.SIM_PRIVILEGED: 2}


def worst_provenance(*items: Provenance | None) -> Provenance:
    ps = [p for p in items if p is not None]
    return max(ps, key=_TRUST.get) if ps else Provenance.ESTIMATED


def derived_provenance(obs: Observation, base: Provenance = Provenance.ESTIMATED, uses_segmentation: bool = False,
                       ) -> Provenance:
    """Taint rule: a detection is as privileged as anything it was computed from: the estimator
    itself (`base`), the pose used for the map transform, the camera frame/extrinsics and, if used,
    the segmentation masks."""
    cam = obs.camera
    return worst_provenance(
        base,
        obs.pose.provenance if obs.pose is not None else None,
        cam.provenance if cam is not None else None,
        cam.segmentation_provenance if (uses_segmentation and cam is not None) else None,
    )


class Detector(Protocol):
    provenance: Provenance

    def detect(self, obs: Observation) -> list[Detection]: ...


@dataclass
class Detection2D:
    label: str
    bbox: tuple[int, int, int, int]  # u0, v0, u1, v1 inclusive
    score: float
    attributes: dict[str, tuple[str, float]] = field(default_factory=dict)
    mask: np.ndarray | None = None  # optional (H,W) bool from a segmenter
    track_id: str | None = None


def point_covariance(obs: Observation, z: float, depth_noise_rel: float = 0.02) -> np.ndarray:
    """Isotropic-ish 3D covariance from pose uncertainty + depth noise (conservative)."""
    var = (depth_noise_rel * z) ** 2
    if obs.pose is not None:
        var += obs.pose.xy_sigma**2 + (z * obs.pose.yaw_sigma) ** 2
    return np.diag([var, var, (depth_noise_rel * z) ** 2])


def _lift(obs: Observation, mask: np.ndarray, max_range: float):
    cam = obs.camera
    T = obs.T_map_camera()
    good = mask & valid_depth(cam.depth, max_range)
    n = int(good.sum())
    if n == 0:
        return None
    vs, us = np.nonzero(good)
    zs = cam.depth[vs, us].astype(float)
    keep = zs <= np.quantile(zs, 0.8) + 1e-9  # front-most samples; robust to background bleed
    pts = backproject(us[keep].astype(float), vs[keep].astype(float), zs[keep], cam.intrinsics, T)
    center = np.median(pts, axis=0)
    extent = np.percentile(pts, 95, axis=0) - np.percentile(pts, 5, axis=0)
    return center, extent, float(np.median(zs)), n, int(mask.sum())


class BoxLifter:
    """2D detections (from `detector_2d(rgb)`) + depth -> 3D Detections."""

    provenance = Provenance.ESTIMATED

    def __init__(
        self,
        detector_2d: Callable[[Observation], list[Detection2D]],
        min_valid_px: int = 20,
        max_range: float = 6.0,
        center_crop: float = 0.6,
    ):
        self.detector_2d = detector_2d
        self.min_valid_px = min_valid_px
        self.max_range = max_range
        self.center_crop = center_crop  # without a mask, use the central part of the bbox

    def detect(self, obs: Observation) -> list[Detection]:
        cam = obs.camera
        if cam is None or cam.depth is None or obs.pose is None:
            return []
        H, W = cam.depth.shape
        prov = derived_provenance(obs)
        out = []
        for d in self.detector_2d(obs):
            if d.mask is not None:
                mask = d.mask
            else:
                u0, v0, u1, v1 = d.bbox
                cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
                hu, hv = (u1 - u0 + 1) * self.center_crop / 2, (v1 - v0 + 1) * self.center_crop / 2
                mask = np.zeros((H, W), bool)
                mask[max(0, int(cv - hv)):min(H, int(np.ceil(cv + hv))), max(0, int(cu - hu)):min(W, int(np.ceil(cu + hu)))] = True
            lifted = _lift(obs, mask, self.max_range)
            if lifted is None or lifted[3] < self.min_valid_px:
                continue
            center, extent, z, n, _ = lifted
            out.append(Detection(
                label=d.label, position=center, position_cov=point_covariance(obs, z), confidence=float(d.score),
                timestamp=cam.timestamp, provenance=prov, attributes=dict(d.attributes),
                track_id=d.track_id, bbox=d.bbox, extent=extent,
            ))
        return out


class SimSegmentationDetector:
    """SIM_PRIVILEGED: rendered instance masks -> Detections. Attributes come from
    `attribute_lookup(seg_id)` (also privileged, e.g. the table number baked into the scene)."""

    provenance = Provenance.SIM_PRIVILEGED

    def __init__(self, min_pixels: int = 30, max_range: float = 6.0,
                 attribute_lookup: Callable[[int], dict[str, tuple[str, float]]] | None = None):
        self.min_pixels = min_pixels
        self.max_range = max_range
        self.attribute_lookup = attribute_lookup or (lambda _id: {})

    def detect(self, obs: Observation) -> list[Detection]:
        cam = obs.camera
        if cam is None or cam.segmentation is None or cam.depth is None or obs.pose is None:
            return []
        seg = cam.segmentation
        out = []
        for seg_id in np.unique(seg):
            label = cam.segment_labels.get(int(seg_id))
            if seg_id == 0 or label is None:
                continue
            mask = seg == seg_id
            lifted = _lift(obs, mask, self.max_range)
            if lifted is None or lifted[3] < self.min_pixels:
                continue
            center, extent, z, n, n_total = lifted
            vs, us = np.nonzero(mask)
            K = cam.intrinsics
            border = us.min() == 0 or vs.min() == 0 or us.max() == K.width - 1 or vs.max() == K.height - 1
            conf = float(np.clip(n / (n + 200.0), 0.2, 0.98)) * (0.7 if border else 1.0) * (0.5 + 0.5 * n / n_total)
            out.append(Detection(
                label=label, position=center, position_cov=point_covariance(obs, z), confidence=conf,
                timestamp=cam.timestamp, provenance=Provenance.SIM_PRIVILEGED,
                attributes=self.attribute_lookup(int(seg_id)), track_id=f"sim:{int(seg_id)}",
                bbox=(int(us.min()), int(vs.min()), int(us.max()), int(vs.max())), extent=extent,
            ))
        return out


class GroundTruthDetector:
    """SIM_PRIVILEGED diagnostic: obs.extra["gt_objects"] = [{id, label, position, attributes?}],
    filtered to the camera frustum so it still behaves like a sensor."""

    provenance = Provenance.SIM_PRIVILEGED

    def __init__(self, max_range: float = 6.0):
        self.max_range = max_range

    def detect(self, obs: Observation) -> list[Detection]:
        T = obs.T_map_camera()
        if T is None:
            return []
        K = obs.camera.intrinsics
        out = []
        for o in obs.extra.get("gt_objects", []):
            p = np.asarray(o["position"], float)
            u, v, z = project_points(p, K, T)
            if not (0 < z[0] <= self.max_range and 0 <= u[0] < K.width and 0 <= v[0] < K.height):
                continue
            out.append(Detection(
                label=o["label"], position=p, position_cov=np.eye(3) * 1e-6, confidence=1.0,
                timestamp=obs.timestamp, provenance=Provenance.SIM_PRIVILEGED,
                attributes=dict(o.get("attributes", {})), track_id=f"gt:{o['id']}",
            ))
        return out
