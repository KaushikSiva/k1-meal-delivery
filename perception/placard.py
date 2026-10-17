"""Table-number placards: texture generator + RGB-only reader (no masks, no simulator labels).

Placard design (proposed scene spec CL-4): a square sign with a saturated orange frame around a
white field showing the table number in a 5x7 bitmap font. Restaurants commonly use numbered
table signs, so this is a deployable visual cue, not an evaluation marker; the robot still has
to find it in the image, read it and lift it to 3D with depth.

Reader pipeline (pure numpy):
  1. orange-frame pixels by hue/saturation/value thresholds,
  2. connected components -> roughly square candidates,
  3. interior crop -> dark-ink bbox -> split into digits by column gaps,
  4. each digit resampled to the 5x7 grid and matched against the font (correlation),
  5. Detection2D(label="table", attributes={"table_number": (digits, conf)}, mask=placard px).
The frame's bottom band is twice as thick: the reader rotates the patch so that band is at the
bottom (any 90-degree multiple) and refuses when orientation is unclear.
Confidence is the worst per-digit match margin; unreadable/ambiguous placards are still reported
as a "table" detection without the attribute (so the executive can VERIFY by moving closer).
"""

from __future__ import annotations

from collections import deque

import numpy as np

from autonomy.contracts import Observation
from .detectors import Detection2D

FRAME_RGB = (255, 120, 0)
FONT = {  # 5 wide x 7 tall, '#' = ink
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
}
GLYPHS = {d: np.array([[c == "#" for c in row] for row in rows], float) for d, rows in FONT.items()}


# ----------------------------------------------------------------------------- texture
def make_placard(number: str | int, size: int = 140, frame_frac: float = 0.1) -> np.ndarray:
    """(size, size, 3) uint8 placard image, readable upright (row 0 = top)."""
    s = str(number)
    if not (1 <= len(s) <= 2 and s.isdigit()):
        raise ValueError("placard supports 1-2 digits")
    img = np.zeros((size, size, 3), np.uint8)
    img[:] = FRAME_RGB
    f = int(round(size * frame_frac))
    fb = 2 * f  # thicker bottom band = orientation cue (like underlining 6 vs 9 on real signs)
    img[f:size - fb, f:size - f] = 255
    inner = size - f - fb
    # glyph cell: text <= 60% of interior height and <= 70% of its width (leaves a white margin
    # so a slightly loose interior crop never clips the digits)
    cell = max(1, int(min(inner * 0.6 / 7, inner * 0.7 / (len(s) * 5 + (len(s) - 1)))))
    gap = cell
    w = len(s) * 5 * cell + (len(s) - 1) * gap
    x0 = f + (size - 2 * f - w) // 2
    y0 = f + (inner - 7 * cell) // 2
    for k, ch in enumerate(s):
        g = np.kron(GLYPHS[ch], np.ones((cell, cell))) > 0.5
        xs = x0 + k * (5 * cell + gap)
        region = img[y0:y0 + 7 * cell, xs:xs + 5 * cell]
        region[g] = 0
    return img


def make_placard_png(number: str | int, path, size: int = 140) -> None:
    """Write the placard texture as PNG (uses only zlib; no PIL needed)."""
    import struct
    import zlib

    img = make_placard(number, size)
    raw = b"".join(b"\x00" + img[r].tobytes() for r in range(img.shape[0]))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


# ----------------------------------------------------------------------------- reader
def orange_mask(rgb: np.ndarray, hue_deg=(10.0, 45.0), min_sat=0.55, min_val=0.25) -> np.ndarray:
    x = rgb.astype(np.float32) / 255.0
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    mx, mn = x.max(-1), x.min(-1)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0)
    hue = np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) % 360
    return (hue >= hue_deg[0]) & (hue <= hue_deg[1]) & (sat >= min_sat) & (mx >= min_val) & (r >= mx - 1e-6)


def components(mask: np.ndarray, min_px: int = 20):
    """4-connected components -> list of (rows, cols) index arrays."""
    H, W = mask.shape
    seen = np.zeros_like(mask, bool)
    out = []
    for r0, c0 in zip(*np.nonzero(mask)):
        if seen[r0, c0]:
            continue
        q = deque([(r0, c0)])
        seen[r0, c0] = True
        rr, cc = [], []
        while q:
            r, c = q.popleft()
            rr.append(r); cc.append(c)
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = r + dr, c + dc
                if 0 <= a < H and 0 <= b < W and mask[a, b] and not seen[a, b]:
                    seen[a, b] = True
                    q.append((a, b))
        if len(rr) >= min_px:
            out.append((np.array(rr), np.array(cc)))
    return out


def read_digits(gray: np.ndarray, min_margin: float = 0.15, min_ink_px: int = 10) -> tuple[str | None, float]:
    """Read 1-2 digits from a placard interior (grayscale, 0..1). Returns (text, confidence)."""
    if gray.size == 0:
        return None, 0.0
    white = np.percentile(gray, 90)
    ink = gray < 0.55 * white
    if ink.sum() < 6:
        return None, 0.0
    rows = np.nonzero(ink.any(1))[0]
    if rows.max() - rows.min() + 1 < min_ink_px:
        return None, 0.0  # too small to read reliably: caller should get closer (VERIFY)
    cols_any = ink.any(0)
    ink = ink[rows.min():rows.max() + 1]
    gray_c = gray[rows.min():rows.max() + 1]
    # split into column runs (digits)
    cols = np.nonzero(cols_any)[0]
    runs, start = [], cols[0]
    for a, b in zip(cols, cols[1:]):
        if b - a > 1 + max(1, int(0.08 * len(cols_any))):
            runs.append((start, a)); start = b
    runs.append((start, cols[-1]))
    ink_h = rows.max() - rows.min() + 1
    if len(runs) == 1 and (runs[0][1] - runs[0][0] + 1) > 1.1 * ink_h:
        # two glyphs merged at low resolution: a single 5x7 glyph is never wider than tall
        a, b = runs[0]
        mid = (a + b) // 2
        runs = [(a, mid - 1), (mid + 1, b)]
    if not 1 <= len(runs) <= 2:
        return None, 0.0
    text, conf = "", 1.0
    for c0, c1 in runs:
        g = 1.0 - gray_c[:, c0:c1 + 1] / max(white, 1e-6)  # ink = high
        h, w = g.shape
        if h < 7 or w < 2:
            return None, 0.0
        if w < 0.45 * h:  # narrow glyph (e.g. "1"): pad to the 5:7 box, centered
            pad = int(round(h * 5 / 7)) - w
            g = np.pad(g, ((0, 0), (pad // 2, pad - pad // 2)))
            h, w = g.shape
        ri = (np.arange(h) * 7 // h)
        ci = (np.arange(w) * 5 // w)
        grid = np.zeros((7, 5))
        cnt = np.zeros((7, 5))
        np.add.at(grid, (ri[:, None].repeat(w, 1), ci[None, :].repeat(h, 0)), g)
        np.add.at(cnt, (ri[:, None].repeat(w, 1), ci[None, :].repeat(h, 0)), 1)
        grid /= np.maximum(cnt, 1)
        v = grid.ravel() - grid.mean()
        scores = {}
        for d, t in GLYPHS.items():
            tv = t.ravel() - t.mean()
            scores[d] = float(v @ tv / (np.linalg.norm(v) * np.linalg.norm(tv) + 1e-9))
        best = sorted(scores, key=scores.get, reverse=True)
        margin = scores[best[0]] - scores[best[1]]
        if scores[best[0]] < 0.5 or margin < min_margin:
            return None, 0.0
        text += best[0]
        conf = min(conf, float(np.clip(0.5 + margin, 0, 0.99)))
    return text, conf


class PlacardReader:
    """detector_2d for BoxLifter: RGB only. Usage: BoxLifter(PlacardReader())."""

    def __init__(self, min_frame_px: int = 30, min_side_px: int = 10, max_aspect: float = 2.5):
        self.min_frame_px = min_frame_px
        self.min_side_px = min_side_px
        self.max_aspect = max_aspect

    def __call__(self, obs: Observation) -> list[Detection2D]:
        cam = obs.camera
        if cam is None or cam.rgb is None:
            return []
        rgb = cam.rgb
        gray = rgb.astype(np.float32).mean(-1) / 255.0
        H, W = gray.shape
        out = []
        for rr, cc in components(orange_mask(rgb), self.min_frame_px):
            r0, r1, c0, c1 = rr.min(), rr.max(), cc.min(), cc.max()
            h, w = r1 - r0 + 1, c1 - c0 + 1
            if min(h, w) < self.min_side_px or max(h, w) / min(h, w) > self.max_aspect:
                continue
            # Orientation: the thick frame band marks the bottom. Rotate the patch upright first;
            # refuse to read if no band is clearly thickest (prevents 6<->9 style misreads).
            fm = np.zeros((h, w), bool)
            fm[rr - r0, cc - c0] = True
            patch = gray[r0:r1 + 1, c0:c1 + 1]
            k = max(2, int(round(0.2 * min(h, w))))
            band = {"bottom": fm[-k:, :].mean(), "top": fm[:k, :].mean(),
                    "left": fm[:, :k].mean(), "right": fm[:, -k:].mean()}
            order = sorted(band, key=band.get, reverse=True)
            text, conf = None, 0.0
            if band[order[0]] - band[order[1]] > 0.12:
                patch = np.rot90(patch, {"bottom": 0, "right": 3, "top": 2, "left": 1}[order[0]])
                ph, pw = patch.shape
                m = int(round(0.13 * min(ph, pw)))
                mb = int(round(0.23 * min(ph, pw)))
                text, conf = read_digits(patch[m:ph - mb, m:pw - m])
            mask = np.zeros((H, W), bool)
            mask[r0:r1 + 1, c0:c1 + 1] = True
            attrs = {"table_number": (text, conf)} if text else {}
            fw = max(1, int(round(0.1 * min(h, w))))  # nominal frame width
            score = float(np.clip(len(rr) / (2 * (h + w) * fw), 0.3, 0.95))
            out.append(Detection2D("table", (int(c0), int(r0), int(c1), int(r1)), score, attrs, mask=mask))
        return out
