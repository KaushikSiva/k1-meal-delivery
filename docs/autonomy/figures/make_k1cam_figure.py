"""Robot's-eye presentation figure: official K1 model, head-camera render (MuJoCo), placard read
by perception/placard.py. Run with the sim environment: sim/.venv/bin/python <this file>.
Labeled on-image: RESTRICTED PLACARD DIAGNOSTIC; privileged sim pose; assumed intrinsics."""

import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests/autonomy")]
from perception.placard import PlacardReader  # noqa: E402
from test_placard import _render_k1_view  # noqa: E402

OUT = Path(__file__).resolve().parent


def main():
    panels = []
    for number, dist in ((3, 1.0), (12, 2.0), (7, 3.0)):
        with tempfile.TemporaryDirectory() as td:
            obs = _render_k1_view(Path(td), number, dist)
        img = Image.fromarray(obs.camera.rgb)
        dr = ImageDraw.Draw(img)
        for d in PlacardReader()(obs):
            u0, v0, u1, v1 = d.bbox
            txt = d.attributes.get("table_number", (None, 0))
            dr.rectangle([u0 - 3, v0 - 3, u1 + 3, v1 + 3], outline=(0, 255, 0), width=3)
            label = f"table {txt[0]} ({txt[1]:.2f})" if txt[0] else "table ? (too far: move closer)"
            dr.rectangle([u0 - 3, v1 + 6, u0 + 8 * len(label), v1 + 22], fill=(0, 0, 0))
            dr.text((u0, v1 + 8), label, fill=(0, 255, 0))
        dr.rectangle([0, 0, 640, 18], fill=(0, 0, 0))
        dr.text((6, 3), f"K1 head camera (MuJoCo render) - placard at {dist:.1f} m", fill=(255, 255, 255))
        panels.append(img)
    W = sum(p.width for p in panels)
    sheet = Image.new("RGB", (W, panels[0].height + 22), (0, 0, 0))
    x = 0
    for p in panels:
        sheet.paste(p, (x, 0))
        x += p.width
    ImageDraw.Draw(sheet).text((6, panels[0].height + 5),
        "RESTRICTED PLACARD DIAGNOSTIC (custom table-number signs) - official K1 model posed, not walking - "
        "sim pose is privileged - camera 640x480/fovy58 assumed pending calibration - not delivery evidence",
        fill=(255, 200, 0))
    sheet = sheet.resize((W // 2, sheet.height // 2))
    sheet.save(OUT / "fig3_k1_headcam_placard_reading.png")
    print("wrote fig3_k1_headcam_placard_reading.png", sheet.size)


if __name__ == "__main__":
    main()
