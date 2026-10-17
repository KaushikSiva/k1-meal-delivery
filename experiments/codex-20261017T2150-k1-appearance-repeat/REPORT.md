# K1 appearance corrected and physics repeated

The actual Isaac renderer now shows a light chest and dark head, arms and legs,
approximating the inspected official Booster product photograph. This is a
per-link material approximation; STL geometry does not provide exact shell
segmentation or textures. No generated image is used as experiment evidence.

![Actual recorded final frame with corrected materials](evaluator_final_recorded.png)

The same trained PPO02 residual, cup-holder fixture and scripted velocity
schedule completed 15 seconds and 3.55766 m, with no drop, maximum payload
movement 3.311 cm and final root speed 0.01756 m/s. The root and payload CSVs
are **byte-identical** to the previous cup-holder PPO transfer trial. This
repeat verifies that the cosmetic change preserved that physical trajectory;
it is not an independent robustness sample or camera-guided delivery.

Two unsuccessful appearance attempts are preserved:

- `failed-import/`: the first material traversal matched no meshes because
  the imported visual subtrees were instances. It stopped before physics.
- `ineffective-binding/`: deinstancing visuals let the second attempt bind
  leaf materials, but stronger ancestor bindings still rendered the robot
  white. The simulation completed; visual inspection rejected the change.

The successful third attempt rebinds the imported object ancestor and asserts
the effective material for every affected mesh. Twenty-three body meshes
changed; collision geometry, masses and joints did not. RGB observations do
change and the manifest records the appearance option.

All 14 artifact hashes were verified. Videos contain 375 frames at 25 fps,
and physical trajectories contain 750 samples at 50 Hz. Raw recordings and
converted USDs remain outside Git. Remote evidence is at
`/home/ubuntu/workspace/k1-runtime/evidence/k1-appearance-03`;
local evidence/source archives are
`runs/brev-k1-20261017/k1-appearance-03-{evidence,source}.tar.gz`.
Preceding attempts retain their corresponding 01 and 02 archives.

Reference: [official Booster K1 product page](https://www.booster.tech/booster-k1/).
See [material scope](../../docs/hardware/K1_APPEARANCE.md).
