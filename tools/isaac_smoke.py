#!/usr/bin/env python3
"""Isaac Sim 5.1 headless physics + RGB smoke test; no K1 or training claims.

Run inside the remote NVIDIA environment with OMNI_KIT_ACCEPT_EULA=YES.
Based on NVIDIA's 5.1 standalone Hello World and Camera Sensors API examples.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
report = {
    "started_at_utc": datetime.now(timezone.utc).isoformat(),
    "evidence_kind": "isaacsim_headless_cube_physics_rgb_smoke",
    "status": "started", "k1_tested": False, "training_performed": False,
    "hardware_tested": False, "delivery_success": None,
    "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "isaacsim_version": metadata.version("isaacsim"),
}
manifest = args.output / "manifest.json"
manifest.write_text(json.dumps(report, indent=2))
app = None
started = time.monotonic()
try:
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "width": 640, "height": 480,
                         "renderer": "RayTracedLighting"})
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid
    from isaacsim.core.utils.numpy.rotations import euler_angles_to_quats
    from isaacsim.sensors.camera import Camera
    from pxr import UsdLux
    import numpy as np
    from PIL import Image

    world = World(stage_units_in_meters=1.0, physics_dt=1 / 60, rendering_dt=1 / 60)
    world.scene.add_default_ground_plane()
    light = UsdLux.DomeLight.Define(world.stage, "/World/light")
    light.CreateIntensityAttr(1000)
    cube = world.scene.add(DynamicCuboid(
        prim_path="/World/cube", name="smoke_cube", position=np.array([0., 0., 1.]),
        scale=np.array([0.5, 0.5, 0.5]), color=np.array([0.9, 0.05, 0.02]), mass=1.0))
    camera = Camera(prim_path="/World/camera", position=np.array([2., 0., 1.5]),
                    frequency=60, resolution=(640, 480),
                    orientation=euler_angles_to_quats(np.array([0, 30, 180]), degrees=True))
    world.reset()
    camera.initialize()
    positions = []
    for step in range(120):
        world.step(render=True)
        positions.append(cube.get_world_pose()[0].tolist())
        if step in (59, 119):
            rgba = camera.get_rgba()
            if rgba.shape != (480, 640, 4):
                raise RuntimeError(f"Unexpected camera buffer shape {rgba.shape}")
            Image.fromarray(rgba[:, :, :3].astype(np.uint8)).save(args.output / f"frame-{step:04d}.png")
    final = np.asarray(positions[-1])
    velocity = cube.get_linear_velocity()
    assert np.isfinite(positions).all() and np.isfinite(velocity).all()
    assert 0.20 < final[2] < 0.30, f"Cube did not settle on ground: {final}"
    assert np.linalg.norm(velocity) < 0.05, f"Cube did not settle: {velocity}"
    rgb = camera.get_rgba()[:, :, :3].astype(float)
    red_pixels = int(((rgb[:, :, 0] > 1.5 * rgb[:, :, 1]) & (rgb[:, :, 0] > 40)).sum())
    assert red_pixels > 100, f"Rendered cube not visible: {red_pixels} red pixels"
    report.update(status="passed", physics_steps=120, final_position_m=final.tolist(),
                  final_velocity_m_s=velocity.tolist(), cube_red_pixels=red_pixels,
                  wall_time_s=time.monotonic() - started)
    (args.output / "positions.json").write_text(json.dumps(positions))
except Exception as exc:
    report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    raise
finally:
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["artifacts"] = {
        p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
        for p in args.output.iterdir() if p != manifest
    }
    manifest.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    if app is not None:
        app.close()
