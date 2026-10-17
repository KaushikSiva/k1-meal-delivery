# Evidence-gated roadmap

No task below is complete merely because it is described here.

| Gate | Deliverable | Required evidence | Owner |
| --- | --- | --- | --- |
| G0 | Team workspace and goal | Readable docs, ownership, truthful status, private GitHub checkpoint | Codex |
| G1 | Contracts and environment audit | Sensor/action definitions, dependency versions, actual host/GPU report, resource blockers | Codex + Claude within allocated paths |
| G2 | CPU autonomy behavior | Tests for search, memory, occlusion, uncertainty and recovery; explicitly software-only | Claude |
| G3 | K1 simulator baseline | Real K1 model loads and steps; compatible locomotion controller; observed sensors; saved config/log/video | Codex |
| G4 | Vision-guided room delivery baseline | Camera-to-action integration, varied starts/goals, no privileged actor state, all attempts counted | Joint integration by Codex |
| G5 | Carrying-controller learning | Actual PPO rollouts/updates/checkpoints and matched held-out results | Codex |
| G6 | VLA learning and integration | Demonstration provenance, actual training, bounded action adapter, held-out improvement/regression analysis | Claude; Codex integration |
| G7 | Transfer preparation | Exported policy runs through deployment path; observation/action parity; calibrated assumptions listed | Codex |
| G8 | Physical K1 validation | Supported load check, standing/walking/stopping trials, camera-guided delivery records | Requires physical K1 and operator |
| G9 | Company pilot qualification | Frozen operating conditions, repeated held-out physical trials, reliability/latency/failure report | Joint |

The first NVIDIA GPU is required at G3 for the full Isaac Sim baseline, before PPO/VLA training. G0–G2 and dependency/interface preparation can proceed on the current computer. Provision only after GPU compatibility, capacity, price and authorized budget are known.

Do not delay baseline/evaluation work to build a polished dashboard. Do not force a model into the product when it regresses the measured task. Preserve the VLA research comparison even if the conventional baseline wins.

## Hardware arrival sequence

Record model/firmware/sensors; collect read-only telemetry; verify camera calibration and time alignment; inspect tray support and manufacturer load guidance; validate joint mappings and control transitions; then conduct supervised supported-load, stationary, short-walk, stop and turn trials before full delivery. A suspended/support-assisted run must be labeled as such.

No physical actuation is currently possible: hardware is absent. Preparation can be completed without claiming successful transfer.
