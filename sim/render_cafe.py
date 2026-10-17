#!/usr/bin/env python3
"""Render the real café USD scene and advance its staged payload physics.

Environment preview only: no robot navigation or delivery success is implied.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--assets", type=Path, default=ROOT / "sim/vendor/cafe-assets")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
report = {"status": "started", "evidence_kind": "isaacsim_cafe_environment_preview",
          "started_at_utc": datetime.now(timezone.utc).isoformat(),
          "robot_present": False, "delivery_success": None, "training_performed": False,
          "source_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [Path(__file__), ROOT / "sim/cafe_scene.py", ROOT / "sim/cafe_assets.json"]}}
manifest = args.output / "manifest.json"
manifest.write_text(json.dumps(report, indent=2))
app = None
try:
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "width": 1280, "height": 720,
                         "renderer": "RayTracedLighting"})
    import numpy as np
    from PIL import Image
    from isaacsim.core.api import World
    from isaacsim.sensors.camera import Camera
    from isaacsim.core.utils.numpy.rotations import euler_angles_to_quats
    from pxr import UsdGeom
    from sim.cafe_scene import build_cafe

    world = World(stage_units_in_meters=1.0, physics_dt=1/60, rendering_dt=1/60)
    report["scene"] = build_cafe(world.stage, args.assets)
    views = [
        ("hero", (0.05, -0.15, 1.65), (0, 7, 0)),
        ("dining", (8.85, -2.9, 1.65), (0, 8, 155)),
        ("robot_height", (0.6, 0.0, 0.9), (0, 10, 0)),
        ("service_counter", (1.2, -0.5, 1.55), (0, 20, 222)),
    ]
    cameras = []
    for name, position, angles in views:
        camera = Camera(prim_path=f"/World/PreviewCameras/{name}", position=np.array(position),
                        orientation=euler_angles_to_quats(np.array(angles), degrees=True),
                        resolution=(1280, 720), frequency=30)
        optics = UsdGeom.Camera.Get(world.stage, f"/World/PreviewCameras/{name}")
        optics.GetHorizontalApertureAttr().Set(36.0)
        optics.GetVerticalApertureAttr().Set(20.25)
        optics.GetFocalLengthAttr().Set(24.0)
        cameras.append((name, camera))
    world.reset()
    for _, camera in cameras:
        camera.initialize()
    for _ in range(90):
        world.step(render=True)
    for name, camera in cameras:
        rgba = camera.get_rgba()
        if rgba.shape != (720, 1280, 4):
            raise RuntimeError(f"Invalid {name} render shape {rgba.shape}")
        rgb = rgba[:, :, :3].astype(np.uint8)
        if float(rgb.std()) < 2:
            raise RuntimeError(f"Blank {name} render")
        Image.fromarray(rgb).save(args.output / f"{name}.png")
    world.stage.Export(str(args.output / "cafe.usda"))
    report.update(status="rendered", physics_steps=90, simulated_seconds=1.5,
                  views=[name for name, _ in cameras])
except Exception as exc:
    report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    raise
finally:
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["artifacts"] = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
                           for p in args.output.iterdir() if p != manifest}
    manifest.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    if app is not None:
        app.close()
