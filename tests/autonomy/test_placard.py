"""Placard reader tests. RESTRICTED PLACARD DIAGNOSTIC (per Codex CL-4): reading custom table-number
signs; this is not general visual destination grounding.

- Synthetic sweep (numpy only): scales, noise and all four 90-degree rotations; asserts ZERO wrong reads.
- K1 head-camera render (needs mujoco>=3.2 MjSpec + Codex's sim/k1_observation.py + vendored
  K1 model; skipped otherwise): official K1 model posed at walking trunk height, assumed
  640x480 / fovy 58 camera (pending calibration), placard on a table at 1.0-3.5 m.
"""

from pathlib import Path

import numpy as np
import pytest

from autonomy.contracts import CameraFrame, CameraIntrinsics, Observation
from perception.placard import PlacardReader, make_placard, make_placard_png

ROOT = Path(__file__).resolve().parents[2]
NUMBERS = list(range(10)) + [10, 12, 23, 47, 58, 80, 99]


def _resize(img, s):
    idx = (np.arange(s) * img.shape[0] / s).astype(int)
    return img[idx][:, idx]


def _read(rgb):
    obs = Observation(0.0, CameraFrame(0.0, CameraIntrinsics(100, 100, 80, 60, 160, 120), np.eye(4), rgb=rgb), None)
    d = PlacardReader()(obs)
    return d, (d[0].attributes.get("table_number", (None, 0))[0] if d else None)


@pytest.mark.parametrize("size,min_rate", [(70, 1.0), (50, 0.95), (40, 0.9), (24, 0.0)])
def test_synthetic_sweep_never_misreads(size, min_rate):
    rng = np.random.default_rng(size)
    ok = total = 0
    for n in NUMBERS:
        for rot in range(4):
            bg = np.full((120, 160, 3), 90, np.uint8)
            p = np.rot90(_resize(make_placard(n), size), rot).astype(float) + rng.normal(0, 8, (size, size, 3))
            bg[30:30 + size, 50:50 + size] = np.clip(p, 0, 255)
            dets, got = _read(bg)
            assert dets, "placard frame not detected"
            assert got in (None, str(n)), f"MISREAD {n} rot{rot} at {size}px -> {got}"
            ok += got == str(n)
            total += 1
    assert ok / total >= min_rate


def test_no_placard_no_detection_and_png_roundtrip(tmp_path):
    rng = np.random.default_rng(1)
    dets, _ = _read(rng.integers(0, 255, (120, 160, 3), dtype=np.uint8) // 3)  # dark clutter
    assert dets == []
    make_placard_png(7, tmp_path / "p.png")
    assert (tmp_path / "p.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def _render_k1_view(tmp_path, number, dist):
    mujoco = pytest.importorskip("mujoco")
    if not hasattr(mujoco, "MjSpec"):
        pytest.skip("mujoco without MjSpec")
    xml = ROOT / "sim/vendor/booster_assets/robots/K1/K1_22dof.xml"
    try:
        from sim.k1_observation import DiagnosticObservationAdapter, sensor_spec
    except Exception as e:  # Codex-owned module missing/incompatible
        pytest.skip(f"sim adapter unavailable: {e}")
    if not xml.exists():
        pytest.skip("vendored K1 model missing")
    png = tmp_path / f"placard_{number}.png"
    make_placard_png(number, png)
    spec = sensor_spec(xml)
    spec.add_texture(name="plac", type=mujoco.mjtTexture.mjTEXTURE_2D, file=str(png))
    mat = spec.add_material(name="placm")
    mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = "plac"
    wb = spec.worldbody
    wb.add_light(pos=[0, 0, 3], dir=[0, 0, -1], diffuse=[0.8, 0.8, 0.8])
    tx = dist + 0.5
    wb.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, pos=[tx, 0, 0.375], size=[0.4, 0.5, 0.375], rgba=[0.6, 0.45, 0.3, 1])
    body = wb.add_body(name="placard", pos=[tx - 0.41, 0, 0.9])
    # plane normal -> -x (faces the robot), spun so the PNG's top is up
    c = np.cos(-np.pi / 4)
    qy, qz = np.array([c, 0, -c, 0]), np.array([c, 0, 0, -c])
    w1, x1, y1, z1 = qy
    w2, x2, y2, z2 = qz
    q = [w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
         w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2]
    body.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0.1, 0.1, 0.01], quat=q, material="placm")
    m = spec.compile()
    d = mujoco.MjData(m)
    d.qpos[2] = 0.545  # trunk height observed in Codex's walking diagnostic
    mujoco.mj_forward(m, d)
    return DiagnosticObservationAdapter(m, diagnostic=True).observe(d)


@pytest.mark.parametrize("number", [3, 6, 9, 12])
@pytest.mark.parametrize("dist", [1.0, 2.0, 3.0])
def test_reads_placard_in_k1_head_camera_render(tmp_path, number, dist):
    obs = _render_k1_view(tmp_path, number, dist)
    dets = PlacardReader()(obs)
    assert len(dets) == 1
    got = dets[0].attributes.get("table_number", (None, 0))[0]
    assert got in (None, str(number))  # never a wrong number
    if dist <= 2.0 or number < 10:
        assert got == str(number)
