# Café lighting preview — attempt 04

Actual Isaac Sim 5.1 RTX renders on the authorized Crusoe L40S, captured
2026-10-17T20:08:26Z–20:08:40Z. This is an environment preview, not a robot trial.

The six-table café contains eighteen textured chairs, plants, a wood floor,
ceiling beams, window daylight and warm pendant lights. Real collision geometry
supports a tray with a dynamic 0.8 kg box and 0.5 kg sealed drink. Dimensions,
masses, friction and lighting are provisional scene choices, not measurements.

![Café view](hero.png)

[Dining view](dining.png) · [Robot-height scene camera](robot_height.png) ·
[Service counter](service_counter.png)

Changes from attempt 03: increase pendant illumination and add a window area
light. Visual inspection confirms the imported textures remain correct and the
interior is legible after enclosing the ceiling. Attempt 02's red material
fallback and attempt 03's underexposure remain preserved in separate reports.
The windows lack a physical glazing model and the exterior is a simple terrace
and sky. No people or dynamic crowds are modeled.

The simulator advanced 90 physics steps (1.5 simulated seconds). All four PNG
SHA-256 values were independently verified against manifest.json after download.
The manifest records exact source hashes. The raw USD (200,983,123 bytes) is
retained on the GPU VM at
`/home/ubuntu/workspace/k1-runtime/evidence/cafe-04/cafe.usda`.
The source bundle and image archive are retained locally under ignored
`runs/brev-k1-20261017/`. Reproduce with sim/CAFE.md.

No robot is present in these images. The robot-height view is a fixed scene
camera, not the articulated K1 sensor. No delivery, learned policy or training
result is established by this preview.

Furniture, floor textures and HDRI: [Poly Haven](https://polyhaven.com/),
[CC0](https://polyhaven.com/license). Exact asset URLs and hashes are locked in
sim/cafe_assets.json.
