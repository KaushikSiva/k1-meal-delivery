#!/usr/bin/env python3
"""Capture actual Isaac café RGB + metric z-depth for offline perception diagnostics.

Fixed scene cameras at assumed K1 head height; simulator extrinsics are privileged.
No robot, labels, segmentation, detector outputs or delivery claims in these inputs.
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
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--assets', type=Path, default=ROOT / 'sim/vendor/cafe-assets')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
manifest = args.output / 'manifest.json'
report = dict(status='started', evidence_kind='isaac_cafe_fixed_camera_rgbd_diagnostic',
              started_at_utc=datetime.now(timezone.utc).isoformat(), robot_present=False,
              training_performed=False, delivery_success=None, provenance='sim_privileged',
              depth_convention='metric optical z; not Euclidean ray distance',
              camera_convention='CV: x right, y down, z forward',
              source_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [Path(__file__), ROOT/'sim/cafe_scene.py', ROOT/'sim/cafe_assets.json']})
manifest.write_text(json.dumps(report, indent=2))
app = None
try:
    from isaacsim import SimulationApp
    app = SimulationApp({'headless': True, 'width': 640, 'height': 480, 'renderer': 'RayTracedLighting'})
    import numpy as np
    from PIL import Image
    from isaacsim.core.api import World
    from isaacsim.sensors.camera import Camera
    from isaacsim.core.utils.numpy.rotations import euler_angles_to_quats
    from pxr import Usd, UsdGeom
    from sim.cafe_scene import build_cafe

    world = World(stage_units_in_meters=1, physics_dt=1/60, rendering_dt=1/60)
    report['scene'] = build_cafe(world.stage, args.assets)
    views = [
        ('table1_1p5', (.5, -2.05, .9), 0),
        ('table1_2p5', (2, .45, .9), -90),
        ('table3_2p0', (4.9, -.05, .9), -90),
        ('table6_2p8', (7.8, -.75, .9), 90),
        ('counter_head_height', (1.25, -2, .9), 180),
        ('counter_elevated_diagnostic', (1.25, -2, 1.35), 180),
    ]
    cameras = []
    focal = 24 / (2 * np.tan(np.deg2rad(58)/2))
    for name, position, yaw in views:
        path = '/World/DiagnosticCameras/' + name
        camera = Camera(prim_path=path, position=np.array(position),
                        orientation=euler_angles_to_quats(np.array([0, 15, yaw]), degrees=True),
                        resolution=(640, 480), frequency=30)
        optics = UsdGeom.Camera.Get(world.stage, path)
        optics.GetHorizontalApertureAttr().Set(32)
        optics.GetVerticalApertureAttr().Set(24)
        optics.GetFocalLengthAttr().Set(float(focal))
        cameras.append((name, camera))
    world.reset()
    for _, cam in cameras:
        cam.initialize()
        cam.add_distance_to_image_plane_to_frame()
    for _ in range(90):
        world.step(render=True)
    report['captures'] = {}
    for name, cam in cameras:
        rgb = np.asarray(cam.get_rgba())[:, :, :3].astype(np.uint8)
        depth = np.asarray(cam.get_depth()).reshape(480, 640).copy()
        assert rgb.shape == (480, 640, 3) and rgb.std() > 2
        depth[(depth <= 0) | ~np.isfinite(depth)] = np.nan
        assert np.isfinite(depth).mean() > .25
        K = np.asarray(cam.get_intrinsics_matrix())
        # USD uses row vectors, local camera +Y up/-Z forward. Convert explicitly
        # to column-vector CV coordinates, avoiding ambiguous ROS doc wording.
        xf = UsdGeom.Xformable(world.stage.GetPrimAtPath(cam.prim_path))
        T = np.asarray(xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T @ np.diag([1, -1, -1, 1])
        assert np.allclose(T[:3, :3].T @ T[:3, :3], np.eye(3), atol=1e-6)
        # Physical check: center-bottom ray lands on the room floor. If blocked by
        # furniture, retain its height as evidence rather than asserting it is floor.
        u, v = 320, 450
        p = T @ np.r_[np.linalg.solve(K, [u, v, 1]) * depth[v, u], 1]
        np.savez_compressed(args.output / (name+'.npz'), rgb=rgb, depth=depth, K=K,
                            T_world_camera=T, timestamp=np.array(1.5),
                            provenance=np.array('sim_privileged'), depth_units=np.array('meters'),
                            depth_convention=np.array('optical_z'), camera_axes=np.array('x_right_y_down_z_forward'))
        Image.fromarray(rgb).save(args.output / (name+'.png'))
        report['captures'][name] = dict(K=K.tolist(), T_world_camera=T.tolist(),
            finite_depth_fraction=float(np.isfinite(depth).mean()),
            bottom_center_world_point_m=p[:3].tolist(), fovy_degrees=58, pitch_down_degrees=15)
    report.update(status='captured', physics_steps=90, simulated_seconds=1.5,
                  limits=['fixed scene cameras, not articulated K1', 'assumed FOV, not calibrated',
                          'perfect simulator extrinsics', 'counter_elevated view exceeds K1 head height'])
except Exception as exc:
    report.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    raise
finally:
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    report['artifacts'] = {p.name: dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size)
                           for p in args.output.iterdir() if p != manifest}
    manifest.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    if app is not None:
        app.close()
