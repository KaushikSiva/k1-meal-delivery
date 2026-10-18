# GR00T with lossless PNG transport

**Two of four loaded delivery conditions passed, versus three of four with the executive alone.** The trained GR00T checkpoint did not improve delivery in this comparison. This batch preserves the same four conditions, checkpoint, inference seed, image pixels and 0.6-second freshness deadline as the preceding raw-RGB batch. Lossless compression changes transport timing and consequently which proposals enter control.

| Condition | Executive baseline | GR00T PNG | VLA-owned ticks | Mean request latency |
|---|---|---|---|---|
| Start left | Pass | Fail | 67 | 0.713 s |
| Start right | Fail | Fail | 412 | 0.554 s |
| Target near left | Pass | Pass | 27 | 0.948 s |
| Target far right | Pass | Pass | 169 | 0.494 s |

The left-start executive declared delivery, but physical evaluation rejected it: room contact, unstable stop and a 66.3-degree peak tray tilt. The right-start run dropped the payload after prolonged room contact. Successful inference and an executive completion state are insufficient evidence of safe delivery. There were no HTTP/model-call failures.

All four manifests and their recorded artifact hashes were checked against the raw local runs. The immutable protocol, source snapshots, physical trajectories, contact records, proposal traces and score files are retained. Images were transported without pixel loss, verified by the transport tests. Inference ran on the authorized L40S through an SSH tunnel; measured synchronous request delay was applied to simulated proposal availability. This is neither a hardware real-time test nor Crusoe Managed Inference.

The baseline and raw-RGB comparison remain available in the parent report. This small, development-only comparison does not establish reliability across layouts, payloads or repeated stochastic runs. The separately measured offline validation-loss reduction must not be presented as a delivery improvement.
