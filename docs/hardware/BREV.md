# Brev compute — 2026-10-17

Native API-key login succeeded in the user-specified organization. The key is
stored only by Brev in owner-only local credential storage, never in this repo.
A verified official v0.6.337 CLI archive was downloaded into ignored
`tools/vendor/brev-0.6.337/`; the installed Homebrew version remains unchanged.
API-key flags are hidden in CLI help; the release source confirms support.
See [official authentication documentation](https://docs.nvidia.com/brev/guides/api-keys).

## Authorized instance

- Name: `k1-isaac-check-20261017`; instance ID: `opqm34emo`.
- Type: Crusoe `l40s-48gb.1x`; one L40S, 48 GB VRAM, 8 vCPUs, 147 GiB RAM, 128 GB disk.
- Catalog rate: $1.74/hour; six compute hours would be $10.44. Account credit balance
  and any separately billed storage have not been established.
- User initially approved a two-hour check, then explicitly extended use for the
  next 5–6 hours including demo **17:15–18:30 America/Los_Angeles**
  (**2026-10-18 00:15–01:30 UTC**). Do not shut down early unless clearly unused.
- The obsolete two-hour guard was cancelled, with its process confirmed terminal.
  **No automatic shutdown is armed.** Reassess usage at the end of the demo.
- No extra instance or more expensive fallback is authorized.

Creation used the exact type, count 1, provider Crusoe, and no Jupyter install.
The dry run succeeded before creation. CLI returned successful creation; live
listing reported DEPLOYING. This is infrastructure evidence, not a working simulator.
The earlier [catalog audit](brev-compute-audit-20261017.json) is a pre-authorization snapshot.

## Next checks

Use `tools/vendor/brev-0.6.337/brev ls --all --json` to observe this same instance.
Do not recreate on observation timeout. Once RUNNING, refresh SSH and inspect
GPU, driver, OS, free storage and installed runtime before installing anything.
Use `brev exec` with the full CLI path above for noninteractive commands.

The pinned Booster training README reports testing with Isaac Lab **2.3.2** and
Isaac Sim **5.1.0**. Start by reproducing that compatibility baseline. NVIDIA now
marks 5.1.0 unsupported; migration needs an explicit compatibility experiment.
[Requirements](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html)
exclude GPUs without RT cores. The [L40S product page](https://www.nvidia.com/en-us/data-center/l40s/)
lists RT cores; this is a suitable candidate, not proof the VM driver/container works.
Source leads were first collected via You.com in you-brev-isaac-compatibility.json.

Planned initial evidence: real `nvidia-smi` output, package/container versions,
Isaac Sim compatibility/startup output, official K1 model load and camera render.
Record failures and all attempt counts. No PPO/VLA training has been performed yet.

Local lifecycle records are under ignored `runs/brev-k1-20261017/`. The cost guard
helper is available for future explicitly bounded trials, but is not active for
this demo reservation and must not be restarted with its old deadline.
