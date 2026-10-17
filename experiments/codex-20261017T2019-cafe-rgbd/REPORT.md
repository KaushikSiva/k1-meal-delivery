# Café RGB-D capture — fixed scene cameras

Six real Isaac Sim RGB/depth captures from the textured café, on the Crusoe L40S.
Five cameras are 0.9 m high, pitched 15 degrees down; a sixth counter view is
explicitly elevated to 1.35 m. FOV58 degrees and camera height are assumptions.
No robot, segmentation, destination labels or trained model is present.

Each ignored `.npz` contains `rgb`, metric optical-z `depth`, `K`,
`T_world_camera` (column vectors; CV x-right/y-down/z-forward), timestamp and
provenance metadata. Exact simulator extrinsics make these privileged inputs.
The accompanying PNGs and manifest are committed; raw observations are retained
locally and at `/home/ubuntu/workspace/k1-runtime/evidence/cafe-rgbd-01/`.
All twelve PNG/NPZ hashes were independently verified after download.

Bottom-center rays from all five head-height views reproject to z=0.003375 m,
within 1.4 mm of the modeled floor finish at z=0.002 m. An independent 25-pixel
patch check per view verifies optical depth and transform conventions jointly.
The initial all-floor patch assertion failed at the counter (2.3 cm height
error): its upper sampled rays hit the lower counter face. The corrected check
uses the nearest analytic intersection with floor z=0.002 m or counter front
x=0.2 m, preserving the original 1 cm error tolerance.
This does not calibrate a physical sensor or establish general depth accuracy.

[Round table at 2 m](table3_2p0.png) · [Counter at head height](counter_head_height.png) ·
[Elevated counter control](counter_elevated_diagnostic.png)

The tabletop is approximately 0.753 m high; the counter top is 1.02 m, above
the assumed head camera. Occlusion, grazing views and furniture appearance are
intended challenges for the offline detector check. Capture source and asset
hashes are in manifest.json; reproduce with `sim/capture_cafe_rgbd.py`.

Furniture, floor textures and HDRI: [Poly Haven](https://polyhaven.com/) (CC0).
