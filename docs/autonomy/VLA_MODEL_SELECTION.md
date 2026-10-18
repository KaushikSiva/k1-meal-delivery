# VLA base-model selection for K1 meal delivery

Author: Claude · 2026-10-17 · Status: written as desk research **before** any training. Sources
are You.com results saved in `docs/autonomy/research/you-vla-*.json`. Third-party comparisons and
forum benchmarks are leads, not verified facts.

> **Update (2026-10-18), what happened after this choice** (Codex's training runs, see the README
> and experiments/):
> - **SmolVLA** (control): 200 updates, validation loss 0.99 → 0.26. Closed loop 2/4, the same as
>   the executive-only baseline (2/4).
> - **GR00T N1.7** (primary): run 02 had 38.9% *worse* validation than its baseline and run 03
>   was 22.3% *better*, so reproducibility isn't established yet. In the image-based closed loop
>   GR00T got 2/4 vs the executive's 3/4.
> - By the decision rule below, **neither VLA beats the executive yet**, so the executive stays in
>   charge and the VLA stays optional.

## What we need the VLA to do (constrains the choice)

- **Output:** a bounded 5-d *local navigation subgoal* (`vla/action_space.py`) at ~1–2 Hz, gated
  by the executive's veto. No joint control and no manipulation (tray carrying is the PPO
  controller's job).
- **Input:** K1 head RGB plus our explicit 16-d memory/state vector and a text task.
- **Runtime:** off-board on the L40S (48 GB) for now. On the robot: Jetson Orin NX-class
  (16 GB shared; K1 spec pages, unmeasured).
- **Implication:** every candidate is pretrained mostly on *manipulation*. Our action head is
  effectively new, so what transfers is the vision-language backbone and embodiment prior, not the
  action expert.

## Candidates

| | **NVIDIA Isaac GR00T N1.7** | **π0.5 (openpi)** | **SmolVLA** | **π0.6 / π*0.6** |
| --- | --- | --- | --- | --- |
| Open weights | Yes (N1.7 "early access") | Yes: `pi05_base` (released Sept 2025) | Yes, `lerobot/smolvla_base` | **No official open weights found.** PI model card (Nov 2025) only; community reimplementation `exla-ai/openpie-0.6` exists |
| Pretraining prior | Real + sim + human video, **includes humanoids** (GR-1, 1X) | 7+ robot configs of real manipulation; strong open-world generalization | Community SO-100-class arm data | n/a |
| Backbone | Cosmos-Reason2-2B (Qwen3-VL arch) in N1.7 (≈3B total per HF name `GR00T-N1.7-3B`) | PaliGemma (Gemma 2B) + action expert | SmolVLM2, ≈450M total | — |
| New-robot path | `launch_finetune.py` + modality config / embodiment tag | openpi TrainConfig; LeRobot PyTorch port | `lerobot-train`, native LeRobot format | — |
| Fine-tune memory | Inference: 16 GB+ GPU (repo); fine-tune req. not confirmed | Inference >8 GB, **LoRA >22.5 GB** (fits L40S 48 GB), full FT >70 GB | Single GPU (docs: ~4 h / 20k steps on an A100, third-party) | — |
| Jetson | Official deployment docs for **Thor and Orin** (Orin: DiT-only TensorRT; JetPack 7.2) | No official Jetson path; forum estimate on Orin NX FP16 **~4–5 Hz** (unverified) | Small enough to try onboard; unmeasured | — |
| License | Code Apache 2.0; weights described as commercially licensable (NVIDIA Open Model License per HF card; repo text says Apache 2.0, a **conflict to resolve**; open GitHub issue #789 asks about "EA" terms) | Code Apache 2.0; **weights subject to Gemma Terms of Use + Prohibited Use Policy** | Apache-2.0 (per model cards seen earlier) | — |
| Sponsor fit | NVIDIA sponsor; Isaac Sim/Lab ecosystem | — | Hugging Face/LeRobot | — |

## Recommendation

1. **Primary candidate: GR00T N1.7.** It's the only one pretrained with humanoids, with an official
   path to adapt a new embodiment and an official Jetson Orin/Thor deployment route. It's
   commercially licensable (pending the license-text check below), and NVIDIA is our sponsor.
2. **Cheap control: SmolVLA.** Fine-tune it first to shake out our data pipeline, action adapter
   and evaluation at low cost. It's the most likely to run onboard an Orin NX.
3. **Strong comparison: π0.5 via openpi, LoRA on the L40S.** It's the best open generalist.
   Before any commercial use, legal must review the Gemma terms on its weights. ~4–5 Hz on an Orin
   NX would still suffice for our 1–2 Hz subgoals, if that unverified number holds.
4. **π0.6: don't plan on it.** There are no official open weights; the community reimplementation
   isn't PI's checkpoint (GOAL.md: don't claim an official π0.6 checkpoint without verification).

**Decision rule (from EVALUATION.md):** whichever model we fine-tune must beat the
**executive-only baseline** on the matched held-out protocol. A VLA that regresses is reported as
such, and the executive stays in charge either way.

## Open checks before committing compute

- [ ] GR00T N1.7 license: read the actual license file and model card (Apache-2.0 vs NVIDIA Open
      Model License; "EA" terms).
- [ ] GR00T fine-tune VRAM and time on one L40S; whether its modality config accepts our 5-d
      subgoal action + 16-d state.
- [ ] K1 Orin NX JetPack version vs GR00T's JetPack 7.2 requirement.
- [ ] Measure inference latency ourselves (L40S off-board; Orin NX when hardware arrives).
- [ ] Data: ~200 sim episodes (VLA_DATA_SPEC.md) from the executive teacher, in **deployable**
      mode only (taint rule), before any model comparison.

## Addendum: Gemini Robotics-ER (user question)

Sources: You.com results `docs/autonomy/research/you-gemini-*.json` (ai.google.dev robotics
docs, DeepMind model pages and blogs, Google developers blog; pricing from a third-party
aggregator).

- **What it is:** a **vision-language model specialized for embodied reasoning**: pointing (2D
  points/boxes), spatial reasoning, multi-step planning, success/progress detection, instrument
  reading, and orchestrating robots and VLAs. It is **not** an action VLA: it doesn't output robot
  actions and **isn't something we fine-tune** (no open weights found).
- **Versions:** ER 1.5 was "available to all developers" via the Gemini API (Google developers
  blog). DeepMind also lists **ER 1.6** and **ER 2** (ER 2 "via the Gemini API, Google AI Studio,
  or the Gemini Enterprise Agent Platform"). Third-party pricing: ER 1.5 preview ~$0.30/$2.50 per
  1M input/output tokens; ER 2 preview ~$1/$5 (unverified with Google).
- **Its fine-tunable sibling, Gemini Robotics On-Device (2):** a VLA that runs locally and adapts
  "with fewer than 200 examples", but access is through a **trusted-tester program** and it was
  built for **bi-arm** robots. It's not a near-term option without access.

**Where ER fits our stack:** the slow, high-level layer, never the control loop.
1. **Instruction grounding:** replace the keyword parser with ER. Handle open-ended requests
   ("the table by the window", "the person in the red shirt") by asking ER to **point** at the
   destination in the head-camera image; lift the point to 3D with depth, as `BoxLifter` does.
   This is unmarked, open-vocabulary grounding, which addresses Codex's "no placard dependence"
   requirement.
2. **Verification:** ER-based success detection as a *second opinion* on "delivered", gated by the
   executive's measured stable-stop check (never instead of it).
3. **Constraints:** it's cloud-only, so latency and availability must never gate stopping or
   balance. Results are ESTIMATED with a model provenance tag, and Google's terms and data
   handling for camera frames need review.

**Recommendation:** use **ER for perception/grounding** (evaluate on the café RGB-D captures:
pointing accuracy vs. known table positions, latency, cost per query) and **fine-tune GR00T N1.7
(or SmolVLA) for the action proposer**. They're complementary, not competing.
