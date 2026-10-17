# K1 visual materials

The official Booster STL model supplies geometry with near-uniform gray visual
materials. Under the café lighting it appears almost entirely white.

The official product photo shows a light silver/white chest with dark head,
arms and legs. `sim/k1_appearance.py` supplies approximate per-link USD surface
materials when the evaluator is launched with `--reference-colors`. It does not
change meshes, collisions, mass, joints or camera placement. It does change RGB
observations, so runs must record whether the option is enabled.

The mesh does not separate every shell, accent and mechanism. These colors are
an approximation, not a scanned or manufacturer-certified textured replica.
We do not add invented branding or use generated images as experiment evidence.

Reference inspected on 2026-10-17:
[official K1 page](https://www.booster.tech/booster-k1/),
[official product photograph](https://fe-cdn.booster.tech/booster-official-website/release-0.1.4/_astro/robot.CSH3ZJyt.webp).
The photograph is retained locally under ignored `runs/k1-appearance/` for
reference; it is not copied into the public repository.
