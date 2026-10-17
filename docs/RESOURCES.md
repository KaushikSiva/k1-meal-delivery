# Resources and access

| Resource | Intended use | Current verified access |
| --- | --- | --- |
| GitHub | Public code/document checkpoints | Public repository verified; reviewed integrated hand-carry checkpoint cbb4264 pushed |
| You.com | Real-world specifications, physical priors, asset references | Live Web Search API verified; local credential in ignored .env; shared client tools/you_search.py |
| NVIDIA Isaac Sim / Isaac Lab | K1 physics, sensors, PPO training | Pinned 5.1.0/2.3.2 installed; real L40S cube physics/RGB smoke passed and café rendered. One documented upstream web-package metadata conflict; no web service used. K1 hand-contact carry verified in MuJoCo and Isaac; separate PPO/VLA training performed |
| Crusoe GPU VM via Brev | Simulator and training | One L40S RUNNING at $1.74/hour; driver580.178.04 verified after upgrade/reboot. Authorized next 5–6 hours including 17:15–18:30 PDT demo; no shutdown timer armed |
| Crusoe Managed Inference | Experiment-agent inference | Credentials unverified |
| Physical K1 | Calibration and transfer evaluation | Not available now; prepare for later arrival |

## Access handling

Use local environment/secrets management for credentials. Report only whether a required credential is available; never print values. Before starting paid jobs, establish an authorized budget and resource limits. Before selecting a VM, verify graphics/simulator requirements for the pinned stack; not every training GPU is suitable for Isaac Sim.

If You.com access is missing, flag it to the user and continue code/interface work. Store future research notes with query, provider, source URL, access date, units, uncertainty and whether a value is measured, manufacturer-specified or estimated. An inferred mass/friction is not calibrated truth.

## Codex continuation

The user cleared the previous goal and activated `end to end is the goal`; status verified active. GOAL.md supplies its concrete scope. Five-minute status updates apply while an agent is actively running. Markdown files alone do not schedule or keep a model running. Each agent loop must obey its status-update instruction and report when idle or waiting.

Official references consulted through the OpenAI Docs skill: [Goals](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex), [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

## W&B training evidence (2026-10-17)

User-authorized logging is in the private
[training project](https://wandb.ai/kaushik-siva88/k1-meal-delivery-20261017).
PPO02 and SmolVLA02 were retrospectively imported with original timestamps,
metrics, configs and checkpoint/source hashes. They are explicitly tagged
`historical-import`; these are not new training jobs. See
[export evidence](../experiments/codex-20261017T2230-wandb-export/REPORT.md).
Credentials remain outside Git. Export uploads only allowlisted manifests/metrics,
with automatic code and Git collection disabled. GR00T completed20-update pilot and two500-update runs. Both saved checkpoints reloaded successfully; validation outcomes differed across the500-update runs. See the GR00T curve reports.
