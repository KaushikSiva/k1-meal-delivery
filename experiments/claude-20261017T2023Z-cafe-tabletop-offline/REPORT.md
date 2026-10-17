# Offline TabletopDetector on Isaac café RGB-D (Claude)

**Evidence kind:** offline perception analysis on Codex's Isaac Sim captures (CL-5). **Privileged** camera poses (sim truth), **no robot present**, no learning. Detector uses depth + pose only (no labels, masks, placards or markers); ground-truth table centers (`sim/cafe_scene.py` TABLES) are used **only to score**.

## Inputs

- `experiments/codex-20261017T2019-cafe-rgbd/` (6 captures; see its manifest for hashes). Five at 0.9 m pitched 15° down, one elevated 1.35 m counter control. FOV 58° assumed.
- Analysis script `analyze.py` sha256 `28b254c2da6cc27c4a18879d36f230180ff7672d8682ae410b7f9e358ecd3160`; detector `perception/tabletop.py` sha256 `004e302e52258b0b73bcc4e2d613e099256617c2c2bd1491eb68d486bf530e1b`; memory `memory/scene_memory.py` sha256 `bad08d4ca6b4c9d38a5bc6f25aa0c9c604681b45adc60fedd5148b37cc40a4ea`. Run: `sim/.venv/bin/python experiments/claude-20261017T2023Z-cafe-tabletop-offline/analyze.py`.

## Results

Target tables ≤ 3 m (the table each capture was aimed at):

| Capture | Table | Range (m) | Detected | Center error after memory (m) | Top z (m, true 0.753) |
| --- | --- | --- | --- | --- | --- |
| table1_1p5 | T1 | 1.5 | yes | 0.183 | 0.741 |
| table1_2p5 | T1 | 2.5 | yes | 0.087 | 0.756 |
| table3_2p0 | T3 | 2.0 | yes | 0.115 | 0.756 |
| table6_2p8 | T6 | 2.8 | **no** | None | None |

- **3/4** target tables detected at 1.5–2.5 m; the 2.8 m one was missed, consistent with the grazing-angle limit seen on MuJoCo renders (head camera ~0.9 m vs 0.753 m top).
- Tables farther than 3 m in view were never detected (expected, not counted as targets).
- **False table tracks: 0** across all 6 captures (chairs, walls, plants, window, counter produced no 'table').
- table1_1p5 produced 2 table detections (top 0.76 m + the beveled rim ~0.73 m); memory's footprint-overlap merge fused them into **1 track**. The rim fragment biases the merged center (0.18 m error, still inside the 0.525 m radius).
- Counter: detected as `counter` at 1.02 m in both counter views. From head height the countertop is above the camera, so that detection is most likely the counter's front lip/edge, not the top. In the elevated view a second `counter` detection at 1.09 m is the **staged payload tray/box on the counter**: a mislabel (no tray class), noted for future pickup work.

## Limitations

- 6 static captures, single lighting, no robot body/occlusion, privileged poses, assumed intrinsics; n is tiny: no rate claims. Detection range ~2.5 m from head height is a real constraint for search (needs approach, head pitch, or placards/appearance cues).

## Artifacts (sha256)
```
28b254c2da6cc27c4a18879d36f230180ff7672d8682ae410b7f9e358ecd3160  analyze.py
971ee97f9986f484ff4394f482dceb9cf9d47acc34d3e23d20e170ce1b012f57  overlay_contact_sheet.png
6ec370ea9ef4b029fa6baa3062a6301b843742800ec628ac2f69f82bf89a78a3  overlay_counter_elevated_diagnostic.png
195957e5107d5032500ff9b0039b2963e1333f2dc8cda0b9e7f371dfdc827cf1  overlay_counter_head_height.png
5202d25bda21a6f62f3ea0e1adb1843cef1d6f21fb43e4e57bba1e804f95dbe6  overlay_table1_1p5.png
7428239820a2e777bcfc953ddf0e233175651e50a633cf0f8bbde34129d64955  overlay_table1_2p5.png
42ec6e932675ba9e6f4d4f4fa6d7c34132320e9abab499753562d5c725501ed4  overlay_table3_2p0.png
f9dc29e6f7e1ab8071ac1b8abd06d7cccac484d1cddeaba883776ebce6a1fa85  overlay_table6_2p8.png
3950b2ccbdac882055904f9de7665ccadedfc70f8f4aa63c89673fe97aacec3c  results.json
```
