# K1 meal delivery — company goal

Build a company robotics system that lets a Booster K1 understand a delivery instruction, find the destination through vision, search, memory and localization, and carry a preloaded pizza box and drink on a tray from one end of a room to the other while maintaining balance and payload stability.

Develop in simulation now and prepare for a physical K1 arriving as soon as tomorrow. Hardware performance remains unverified until measured on the real robot. Company progress and honest learning take precedence over winning the hackathon. Failed experiments are valid results; fabricated progress is not.

## Required behavior

1. Accept a delivery instruction and identify the intended destination from visual observations.
2. Search when the destination has never been seen; remember observations when it leaves view; relocalize when pose confidence is insufficient.
3. Navigate around obstacles using live observations and feedback. Vary starts, destination locations, layouts and payloads.
4. Carry the tray, pizza box and drink; decelerate and stop steadily at the correct destination.
5. Detect uncertainty and failure. Stop, observe, replan or report inability to proceed instead of silently inventing state.
6. Train actual models: investigate VLA fine-tuning for task actions and PPO training/fine-tuning for carrying control. Establish baselines and quantify each contribution separately.
7. Export and run the trained controller through a K1-compatible deployment path, first in simulation and later on hardware.

## Initial scope

A person loads a suitably supported tray. Begin with a lightweight box and sealed drink, level indoor floors and static obstacles. Initial delivery ends with a stable stop; autonomous pickup, placement, door opening and open-cup transport are later milestones. Record all attachments, restraints and assistance.

The baseline is vision-guided. Marker following, fixed action replays and perfect simulator localization may be explicitly labeled diagnostic tests, but cannot satisfy the delivery goal. Evaluation-only markers must not leak into the policy's observations or act as hidden destination hints.

## Learning architecture

Camera observations and robot telemetry feed perception, localization and explicit scene memory. A task executive handles search, tracking, recovery and completion. A VLA candidate proposes bounded actions/subgoals through a documented interface. Navigation checks feasibility and the carrying controller executes commands. A single actuator-command owner arbitrates control.

SmolVLA is an initial candidate, not a verified K1 policy. Public model availability, camera/action compatibility, training data and runtime must be checked. Do not assume that a public VLA checkpoint understands this robot or already supplies long-term memory. Do not claim an official pi0.6 checkpoint is available without verifying it.

PPO must collect genuine simulator rollouts and update real policy weights. A residual controller around an established K1 locomotion baseline is a candidate requiring validation. A VLA and PPO are separate learning components, not interchangeable labels.

## Evidence and completion

- Record every experiment: hypothesis, exact change, config/code versions, checkpoint hashes, training budget, evaluation protocol, outcomes, screenshots, continuous videos and failure analysis.
- Report successes/attempts and uncertainty, plus falls, drops, collisions, interventions, time, destination error and payload motion. Separate simulation, cross-simulator and hardware results.
- Use held-out layouts, seeds and payloads. Equalize training budgets when comparing curricula. Keep failed and negative experiments.
- Never report an unmeasured value as zero or invent a percentage. No training or physical success is established by this document.
- Freeze task tolerances and acceptance thresholds before evaluation. Fine-tuning is an improvement only if matched evaluation supports it.
- The simulation milestone requires an integrated camera-to-action run and reproducible baseline/learning comparisons. Hardware completion requires repeated physical K1 trials under the declared setup and protocol; export alone is insufficient.

## Sponsors and resources

- **You.com:** primary research channel for real-world specifications, material/asset references and parameter priors. Preserve source URLs, units, dates and uncertainty; web estimates are not physical measurements.
- **NVIDIA:** Isaac Sim room assets, Isaac Lab training and compatible robotics tools. Pin tested versions and check asset licenses and sensor compatibility.
- **Crusoe:** GPU VM for simulation/training; Managed Inference for experiment agents. Inference credits do not establish GPU capacity or training credit eligibility.
- Tell the user when API credentials, funded compute or hardware are missing. Never put secrets in Markdown, Git, logs or screenshots.

## Continuous teamwork

Codex and the user's Claude agent work as teammates using [AGENTS.md](AGENTS.md), [coordination/OWNERSHIP.md](coordination/OWNERSHIP.md), and separate Markdown status and handoff files. Each agent updates its status at least every five minutes during active work and immediately after major changes, failures or handoffs. Read the other agent's updates before claiming work or changing shared contracts.

Commit and push meaningful, reviewed checkpoints to the private GitHub repository. Keep large datasets, weights and raw recordings out of Git; publish manifests and verified artifact references.

## Platform goal status

The user cleared the old goal and activated the platform goal `end to end is the goal` on 2026-10-17. The goal tool verified status `active`. This file defines the concrete end-to-end objective and evidence requirements for that goal. Keep working toward it; do not mark it complete after repository setup or simulation-only results.
