# Resources and access

| Resource | Intended use | Current verified access |
| --- | --- | --- |
| GitHub | Private code/document checkpoints | Repository created; first push pending at bootstrap |
| You.com | Real-world specifications, physical priors, asset references | Live Web Search API verified; local credential in ignored .env; shared client tools/you_search.py |
| NVIDIA Isaac Sim / Isaac Lab | K1 physics, sensors, PPO training | No installed working stack verified |
| Crusoe GPU VM | Simulator and training | No VM, budget or GPU capacity verified |
| Crusoe Managed Inference | Experiment-agent inference | Credentials unverified |
| Physical K1 | Calibration and transfer evaluation | Not available now; prepare for later arrival |

## Access handling

Use local environment/secrets management for credentials. Report only whether a required credential is available; never print values. Before starting paid jobs, establish an authorized budget and resource limits. Before selecting a VM, verify graphics/simulator requirements for the pinned stack; not every training GPU is suitable for Isaac Sim.

If You.com access is missing, flag it to the user and continue code/interface work. Store future research notes with query, provider, source URL, access date, units, uncertainty and whether a value is measured, manufacturer-specified or estimated. An inferred mass/friction is not calibrated truth.

## Codex continuation

The user cleared the previous goal and activated `end to end is the goal`; status verified active. GOAL.md supplies its concrete scope. Five-minute status updates apply while an agent is actively running. Markdown files alone do not schedule or keep a model running. Each agent loop must obey its status-update instruction and report when idle or waiting.

Official references consulted through the OpenAI Docs skill: [Goals](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex), [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
