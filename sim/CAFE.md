# Common Table café environment

The user requested the most realistic practical scene for the hackathon demo,
while preserving the company goal of real camera-guided, physics-based delivery.
The initial scene is an invented 10.4 × 7.2 m café with six dining tables,
eighteen chairs, plants, daylight, warm pendant lights and a service counter.
A tray, pizza box and sealed drink are staged on the counter. The robot is not
yet integrated into this USD scene; environment renders are not delivery trials.

## Assets and reproducibility

Furniture, wood floor textures and HDRI are by [Poly Haven](https://polyhaven.com/),
under [CC0](https://polyhaven.com/license). Their live API requests attribution;
retain this credit in presentation notes. Source discovery is recorded in
`docs/hardware/you-realistic-cafe-*-20261017.json`.

`cafe_assets.json` fixes all 24 files by URL, byte count and SHA-256. The original
USD bundles referenced roughness EXRs absent from their API include lists; both
missing files were fetched, verified and added to the lock. Do not replace assets
with new versions silently.

```sh
python3 tools/fetch_cafe_assets.py
# In the prepared Isaac Sim environment:
OMNI_KIT_ACCEPT_EULA=YES python sim/render_cafe.py --output experiments/UNIQUE-cafe-preview
```

Assets live in ignored `sim/vendor/cafe-assets/`. No assets or credentials are
embedded in Git. The USD stage references local paths; rerun the builder after
fetching assets on another machine. Preview manifests contain source and image
hashes. `status=rendered` means environment images exist, not that a robot delivered.
Isaac's native shutdown can mask Python failures with process exit0; always check
the manifest status as the remote launcher does.

## Geometry and physics

- Z-up, meters. Native table assets are scaled uniformly to ~0.753 m height and
  1.05 m diameter. Chairs retain their native dimensions. These are scene choices,
  not a venue survey or hardware measurement.
- Table/chair visual meshes are also static triangle-mesh colliders. The floor,
  walls, counter and tray have primitive collision geometry. Plants use a pot
  collision proxy; their leaves do not collide.
- The window has an invisible collision pane. Actual glazing, reflection and
  depth-sensor response are not modeled; do not use this scene to validate glass
  detection.
- Box mass0.8kg, drink mass0.5kg and friction0.7static/0.6dynamic are provisional
  modeling assumptions. The tray is supported by the counter, not robot hands.
  A loaded walking trial still needs the attachment/support model, real control,
  frozen evaluation thresholds and recorded payload motion.
- No people or dynamic crowds yet. The first layout is a development scene and
  must not become a held-out evaluation layout.

## Verified preview and planned integration

The verified [four-view GPU preview](../experiments/codex-20261017T2008-cafe-lit-preview/REPORT.md)
uses explicit PreviewSurface texture bindings and enclosed-room lighting.
Earlier material and exposure failures are preserved alongside it.

Local USD checks verify metric scale/grounding, resolved texture dependencies,
furniture collisions and payload mass attributes. They require `usd-core==26.8`
in the separate local CPU environment (`.venv`), not in the Isaac environment:

```sh
.venv/bin/python -m pytest tests/sim/test_cafe_scene.py -q
```

Remote preview emits hero, dining, robot-height and service-counter views. The
robot-height preview camera is a scene camera, not yet the articulated K1 sensor.
Integrate the pinned K1 model/controller, articulated RGB-D camera, autonomy
session, live obstacle observations and payload evaluation before calling this
an end-to-end delivery scene. Presentation views remain separate from actor input.
