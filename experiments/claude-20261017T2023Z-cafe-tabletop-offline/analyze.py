"""Offline, read-only: TabletopDetector on Codex's Isaac café RGB-D captures (CL-5).
Inputs are privileged (sim poses); no robot present. Ground truth (table centers) used only to score."""
import hashlib, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from autonomy.contracts import CameraFrame, CameraIntrinsics, Observation, Pose2D, PoseEstimate, Provenance
from memory import SceneMemory
from perception.geometry import project_points
from perception.tabletop import TabletopDetector

SRC = ROOT / "experiments/codex-20261017T2019-cafe-rgbd"
OUT = Path(__file__).resolve().parent
TABLES = [(x, y) for x in (2.0, 4.9, 7.8) for y in (-2.05, 2.05)]  # sim/cafe_scene.py TABLES (evaluation only)
R_TABLE, TOP = 0.525, 0.753
rows, panels = [], []
for f in sorted(SRC.glob("*.npz")):
    z = np.load(f, allow_pickle=True)
    K, depth, rgb = z["K"], z["depth"].astype(np.float32), z["rgb"]
    H, W = depth.shape
    intr = CameraIntrinsics(float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2]), W, H)
    t = float(z["timestamp"])
    cam = CameraFrame(t, intr, z["T_world_camera"], rgb=rgb, depth=depth, provenance=Provenance.SIM_PRIVILEGED)
    obs = Observation(t, cam, PoseEstimate(Pose2D(0, 0, 0), np.zeros((3, 3)), t, "sim_gt", Provenance.SIM_PRIVILEGED))
    dets = TabletopDetector().detect(obs)
    mem = SceneMemory()
    mem.update(obs, dets)
    tracks = [o for o in mem.objects.values() if o.label == "table"]
    cpos = z["T_world_camera"][:3, 3]
    # visible-in-range tables (evaluation): center projects into image and is within 3.5 m
    for k, (x, y) in enumerate(TABLES):
        u, v, zc = project_points(np.array([[x, y, TOP]]), intr, z["T_world_camera"])
        rng = float(np.hypot(x - cpos[0], y - cpos[1]))
        in_view = zc[0] > 0 and 0 <= u[0] < W and 0 <= v[0] < H
        if not in_view:
            continue
        hit = [o for o in tracks if np.hypot(o.position[0] - x, o.position[1] - y) <= R_TABLE]
        rows.append({"capture": f.stem, "table": f"T{k + 1}", "range_m": round(rng, 2),
                     "detected": bool(hit), "center_err_m": round(float(np.hypot(hit[0].position[0] - x, hit[0].position[1] - y)), 3) if hit else None,
                     "top_z": round(float(hit[0].position[2]), 3) if hit else None})
    false_tables = [o for o in tracks if min(np.hypot(o.position[0] - x, o.position[1] - y) for x, y in TABLES) > R_TABLE]
    counters = [d for d in dets if d.label == "counter"]
    rows.append({"capture": f.stem, "summary": True, "n_table_dets": sum(d.label == "table" for d in dets),
                 "n_table_tracks_after_memory": len(tracks), "false_table_tracks": len(false_tables),
                 "counter_dets": [[round(float(c), 2) for c in d.position] for d in counters]})
    im = Image.fromarray(rgb)
    dr = ImageDraw.Draw(im)
    for d in dets:
        ex = d.extent
        cx, cy, cz = d.position
        corners = np.array([[cx + sx * ex[0] / 2, cy + sy * ex[1] / 2, cz] for sx in (-1, 1) for sy in (-1, 1)])
        u, v, zc = project_points(corners, intr, z["T_world_camera"])
        if (zc > 0).all():
            order = [0, 1, 3, 2, 0]
            dr.line([(float(u[i]), float(v[i])) for i in order], fill=(0, 255, 0) if d.label == "table" else (0, 200, 255), width=3)
            dr.text((float(u.min()), float(v.min()) - 12), f"{d.label} top {cz:.2f} m", fill=(0, 255, 0))
    dr.rectangle([0, 0, W, 16], fill=(0, 0, 0))
    dr.text((4, 2), f"{f.stem}: depth-geometry detections (no labels/markers); Isaac capture, privileged pose, no robot", fill=(255, 255, 255))
    panels.append(im)
    im.save(OUT / f"overlay_{f.stem}.png")
sheet = Image.new("RGB", (640 * 3, 480 * 2))
for i, p in enumerate(panels[:6]):
    sheet.paste(p, ((i % 3) * 640, (i // 3) * 480))
sheet.resize((960, 480)).save(OUT / "overlay_contact_sheet.png")
(OUT / "results.json").write_text(json.dumps(rows, indent=1))
for r in rows:
    print(r)
