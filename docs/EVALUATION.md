# Experiment and evidence protocol

Current robotics metrics: **unmeasured**. There are no project training runs or physical trials yet.

## Freeze before evaluating

Version a protocol containing room geometry, start/target distributions, payload/attachment details, time limit, stopping tolerance, stable-stop duration, collision/drop/fall definitions and sensor availability. Define thresholds before comparing checkpoints. Keep a development set separate from a held-out final set; changes after inspecting final results require a new held-out set and disclosure.

Every trial begins when an accepted delivery command is issued. Failures, timeouts and operator interventions count in the denominator. Infrastructure failures remain visible with reasons; report requested, started, completed and excluded counts. Do not silently remove inconvenient trials.

## Core measurements

- Delivery success: successful qualifying deliveries / all qualifying attempts; show raw counts and uncertainty.
- Falls, drops, collisions, intervention counts and reasons.
- Completion time (success-only clearly labeled) and time-to-failure for unsuccessful trials.
- Destination error, peak/RMS tray tilt, payload displacement, relevant acceleration and inference latency where actually measured.
- Training environment steps, optimizer steps, demonstrations, wall time, GPU type/hours and known costs.
- Open-cup experiments additionally measure spillage; tilt is only a proxy and cannot prove spill-free transport.

Keep simulation, cross-simulator and hardware tables separate. Test fixtures, synthetic state-machine tests and fabricated example data never enter robotics result tables. Unknown values are null/unmeasured, not zero.

## Comparisons

1. Established loaded locomotion + conventional vision/navigation baseline.
2. Same navigation with PPO-fine-tuned carrying control.
3. Same validated carrying control with a fine-tuned VLA action layer.
4. Combined system; ablations for memory, physical randomization and agent-designed curriculum where useful.

Use matched conditions/seeds and equal budgets when attributing effects. Report both success-rate percentage-point change and relative change where defined. When baseline success is zero, relative percentage improvement is undefined. Multiple training seeds and confidence intervals are needed before generalizing beyond one run. Do not select a checkpoint using final test performance.

## Per-experiment record

Create an immutable `experiments/<agent>-<UTC>-<slug>/REPORT.md` containing:

- Hypothesis, parent checkpoint, exact change, author and timestamp.
- Code/config hashes, dependencies, dataset split IDs and observation/action definitions.
- Full commands, resources, training logs and checkpoint artifact hashes.
- Protocol version; success/attempt counts; every failure classification; limitations and uncertainty.
- Links to actual trial videos and screenshots, with trial ID, timestamp, checkpoint and view provenance.
- Conclusion: improvement, regression, inconclusive or blocked; next discriminating experiment.

Capture start, approach, stop and failure frames at consistent events, plus continuous recordings of evaluation trials. Highlight reels must link to the complete trial manifest. Keep large media/checkpoints outside Git, with checksums and storage references in the report. Do not manufacture images or curves.

## Progress ledger

Use evidence states: planned → implemented → software-tested → simulator-tested → trained → hardware-tested. These are capability-specific; progress in one does not imply the next. A failed experiment can close a hypothesis without advancing a capability.
