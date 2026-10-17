# VLA demonstration data and bounded action adapter — proposal

Author: Claude · Status: **spec + interface code + software tests only**. No model has been
downloaded, fine-tuned or evaluated, and no demonstrations exist yet.

## 1. What we know (sourced) vs. assume

Facts below come from You.com searches (raw results in `docs/autonomy/research/*.json`, retrieved
2026-10-17). They are source leads, not verified by running anything.

| Item | Source lead | Status |
| --- | --- | --- |
| SmolVLA ≈ 450M params; inputs = multiple camera views + robot sensorimotor state + language instruction; output = an **action chunk** | huggingface.co/blog/smolvla, huggingface.co/docs/lerobot/en/smolvla | documentation claim |
| Flow-matching action expert; VLM frozen during training; 10 flow steps at inference | arxiv.org/html/2506.01844v1 | paper claim |
| 50-step action chunks appear in published SmolVLA fine-tunes | a third-party model card on huggingface.co | third-party; check `smolvla_base` config when pinned |
| Images are resized with padding to 512×512 internally | a third-party fine-tune model card | third-party; verify in pinned lerobot |
| Fine-tuning CLI: `lerobot-train --policy.path=lerobot/smolvla_base --dataset.repo_id=…` | lerobot docs | documentation |
| Docs report 25 episodes was **not enough** for their task | lerobot SmolVLA docs | anecdotal |
| LeRobotDataset v3 packs many episodes per parquet/MP4 file (v2 = one per episode) | huggingface.co/docs/lerobot/lerobot-dataset-v3 | documentation |
| K1: stereo depth camera, 2-DOF head, ~0.4 m/s walking, Jetson Orin NX-class compute (48–200 TOPS by edition) | booster.tech/booster-k1 and reseller pages | manufacturer/reseller claims, **unmeasured** |

Assumptions we must **not** make:

- that `smolvla_base` understands a humanoid, a velocity/subgoal action space, or our camera height;
- that it has memory or SLAM (it doesn't: we inject memory explicitly);
- that it can run onboard at a useful rate (latency on Orin is unmeasured).

SmolVLA was pretrained on community **arm manipulation** data. Our action space is new, so the
action expert is effectively learned from our data.

## 2. Role of the VLA in the stack

The VLA **proposes local subgoals** at ~1–2 Hz; it doesn't command joints and doesn't decide task
completion.

```
obs + memory ──► VLA ──► VLAProposal (normalized chunk) ──► BoundedActionAdapter ──► AutonomyCommand
                                                                 ▲                       (selected_by="vla")
            DeliveryExecutive command (fallback, safety owner) ──┘
```

`vla/adapter.py` rules:

1. **Executive-only states**: RELOCALIZE, SENSOR_WAIT, FINAL_APPROACH, SETTLE, DONE, FAILED, and
   any STOP. The VLA is ignored there.
2. **Rejected**: stale proposals (> 0.6 s after the conditioning observation), non-finite values,
   wrong dimension.
3. **Clipped**: values outside the bounds below.
4. **Feasibility**: the subgoal must be in a free cell of the inflated map, with a planned path
   ≤ 2× the straight-line distance + 0.3 m. Otherwise the proposal is rejected.
5. **Speed**: ≤ the executive's current cap, including the degraded-localization cap.
6. A VLA `hold` becomes HOLD with a short TTL (0.8 s). The VLA can never emit STOP or "delivered".
7. Every decision is logged (`AdapterDecision`) and every command labeled, so evaluation can
   attribute behavior to the VLA or the executive.

Software tests: a teacher-imitating fake VLA completes the fixture delivery through the adapter. A
random fake VLA can't move the robot while localization is lost or exceed speed caps, and NaN
actions are rejected.

## 3. Action space (`vla/action_space.py`)

One normalized row a ∈ [-1, 1]^5 per chunk step. The adapter uses the first row; later rows are
kept for analysis and for temporal ensembling later.

| Index | Name | Physical range | Meaning |
| --- | --- | --- | --- |
| 0 | dx | [-0.3, 1.5] m | subgoal forward offset, base frame |
| 1 | dy | [-0.8, 0.8] m | subgoal lateral offset |
| 2 | dyaw | [-π/2, π/2] rad | heading change at the subgoal |
| 3 | speed | [0, 0.35] m/s | requested speed (capped again by the executive) |
| 4 | hold | ≥ 0 → hold | stop and observe |

Why subgoals rather than velocities or joints:

- they keep the VLA at a rate it can plausibly sustain;
- they let navigation check feasibility;
- they leave balance and tray stability to the PPO / carrying controller, keeping the VLA and PPO
  learning problems separate (GOAL.md).

The executive's commands map into this space (`vla/recorder.label_from_command`: a carrot 1 m along
the planned path, projected from the robot's position), so the scripted executive can act as the
teacher.

## 4. Inputs with explicit memory (`vla/inputs.py`)

LeRobot-style feature names:

| Feature | Shape | Content |
| --- | --- | --- |
| `observation.images.head` | H×W×3 uint8 | head RGB (depth not consumed by SmolVLA as-is; open question) |
| `observation.state` | 16 float32 | target hypothesis in base frame (dx, dy, dist), confidence, age, verdict; localization σ and status; measured base twist; phase one-hot. Full layout is in `vla/inputs.py`. |
| `task` | str | instruction + executive state + text memory summary (e.g. `table 3:confirmed 2.1m at +35deg, seen 4s ago`) |

These features are built from the estimated pose and scene memory. Their provenance is only as
good as the detector that fed memory. If memory was built from privileged masks or labels (e.g.
`SimSegmentationDetector`), then `observation.state` and the `task` memory text are **privileged**,
even though the RGB image is not. Such data can't be used to claim deployable VLA performance.

## 5. Demonstration data plan

**Teachers**, in order of availability:

1. **Scripted executive in simulation** (cheap, many episodes). Run in Codex's K1 sim with the
   follower + walking policy.
   - Label provenance `teacher=executive`.
   - If the sim run uses a privileged detector (rendered masks/labels) or privileged pose, the
     episode is tagged `privileged_inputs=[...]`. **Every memory-derived feature in it
     (`observation.state`, `memory_text`) is privileged too**, not just the masks. Only the raw RGB
     and truly sensor-derived signals are deployable.
   - Privileged episodes may be used for pipeline debugging or as an explicitly labeled
     privileged-teacher ablation. They can't support a deployable-performance claim. Deployable
     demonstrations require a deployable detector and pose source end to end.
2. **Teleoperated sim episodes** for recovery behaviors the executive handles poorly.
3. **Real K1 episodes** once hardware arrives (teleop with a loaded tray). Required before any
   hardware claim.

**Per-step record** (`vla/recorder.py`, JSONL + NPZ now; LeRobotDataset v3 conversion once
`lerobot` is pinned):
`episode_id, frame_index, timestamp, task, memory_text, executive_state, command_kind, selected_by,
observation.state[16], action[5], image_ref`.

**Per-episode meta**: outcome, n_frames, provenance (`source ∈ {fixture, mujoco, isaac, k1}`,
detector, privileged inputs, sim/scene seed, layout id, payload config, code hash).

**Variation** (GOAL.md): start poses, destination tables and numbers, layouts (held-out set),
occluders and passers-by, lighting/textures, camera height/pitch jitter, pose-noise levels,
payloads. **Splits** are by layout and seed (no frame-level leakage).

**Size**: unknown until tried. The docs anecdote suggests well beyond 25 episodes per task variant.
Start with ~200 sim episodes for a pipeline check, then decide by matched held-out evaluation.

**Not in the dataset**: ground-truth poses as inputs, object ids, success markers, raw video in Git
(store externally with hashes; GOAL.md).

## 6. Training and evaluation plan (to execute once GPU and sim exist)

1. Pin `lerobot` and `smolvla_base` revisions; record hashes.
2. Configure the 5-d action / 16-d state features; check the chunk length vs. our 1–2 Hz proposal
   rate.
3. Fine-tune on a fixed training budget, recording steps, GPU type/hours and cost.
4. Matched evaluation on held-out layouts, all with the same carrying controller:
   - (a) executive only;
   - (b) VLA through the adapter;
   - (c) VLA with the memory features ablated.
   Report success/attempts, adapter rejection rate by reason, latency and failure classes. A
   regression is a valid result.
5. Measure onboard vs. off-board latency before deciding where the VLA runs. Cloud loss must leave
   the executive and follower (local) in control.

## 7. Open questions

- **Q-VLA1.** Does Codex's sim camera match K1 head intrinsics and mount? (Affects
  transferability of images.)
- **Q-VLA2.** Depth: SmolVLA consumes RGB views. Options: pass depth as a pseudo-RGB extra view, or
  rely on the memory state vector. Needs an experiment.
- **Q-VLA3.** Which GPU (Crusoe) for fine-tuning? SmolVLA is advertised as single-GPU trainable;
  Isaac Sim needs RT-core GPUs (Codex note), which may be a different machine.
