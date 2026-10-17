# Final PPO checkpoint: farther travel, still a dropped drink

One matched development comparison in the actual rendered Isaac café. Same
supported tray, free box/drink, initial pose, physics settings and requested
15-second command schedule as the unchanged-actor loaded baseline. The candidate
uses the final checkpoint after the predeclared 100 PPO iterations; no checkpoint
selection based on this evaluation. This is scripted locomotion, not navigation.

| Measurement | Unchanged actor | Trained residual + frozen actor |
| --- | ---: | ---: |
| Termination | Drink dropped | Drink dropped |
| Simulated duration before drop | 6.442 s | 12.126 s |
| Net forward travel | 1.246314 m | 3.229679 m |
| Peak body tilt | 3.381482° | 4.003213° |
| Peak payload tilt | 104.2543° | 115.0622° |
| Maximum horizontal payload displacement | 0.310774 m | 0.205415 m |
| Development stability pass | False | False |

The candidate carried farther before the drink fell, but **both trials failed**.
This single development pair does not establish repeatable improvement, a success
rate or delivery capability. Neither run reached the requested stop phase at13s.
The box stayed on the tray; the drink tipped/slid off. There is no liquid model,
rim, cup holder or restraint. The rigid torso bracket is explicitly modeled and
has mass; no hand grasp is claimed.

The candidate checkpoint records204,800 environment transitions/1,600 optimizer
updates. Its SHA256 matches the independently checked training checkpoint.
Its actor inputs are only the existing K1 telemetry/command/history signals plus
previous residuals; payload/world truth are evaluation-only here.

Twelve downloaded artifact hashes and all executed source hashes were verified.
Both videos contain303frames at25fps (12.12s); root/payload CSVs contain606samples
at50Hz. The last6ms before termination are absent from those sampled recordings,
but included in per-physics-step termination and maximum metrics. Original
baseline recordings similarly stop2ms before termination.

Visual-review limitation: the fixed evaluator camera loses the robot as it walks
beyond the initial area (evaluator-0250.png shows the empty starting area).
Consequently that video does not visually establish the final drink drop; the
drop is measured from actual physics state. The head camera continues recording.
A wider evaluator view and repeat trials are needed for a complete visual
comparison. The existing recordings are preserved without editing this out.

The actual trained actor also exported to CPU TorchScript with zero error on32
test observations, maintaining the±0.08rad output bound. This is export/interface
evidence, not hardware readiness. Export metadata is preserved separately in the
training evidence directory; weights remain outside Git.

Original remote: `/home/ubuntu/workspace/k1-runtime/evidence/k1-loaded-ppo02-eval01`.
Local evidence/source archives:
`runs/brev-k1-20261017/k1-loaded-ppo02-eval01-{evidence,source}.tar.gz`.
Baseline: [loaded01](../codex-20261017T2043-k1-loaded-baseline/REPORT.md).
Training: [PPO02](../codex-20261017T2054-ppo-training/REPORT.md).
