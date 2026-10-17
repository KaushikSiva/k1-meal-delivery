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
The dry run succeeded before creation. Live listing subsequently reported
RUNNING/HEALTHY; SSH access and post-upgrade GPU visibility are verified.
Headless Isaac Sim physics and RGB rendering are now verified on this instance.
K1 integration and training in Isaac remain outstanding.
The earlier [catalog audit](brev-compute-audit-20261017.json) is a pre-authorization snapshot.

## Runtime preparation

Use `tools/vendor/brev-0.6.337/brev ls --all --json` to observe this same instance.
Do not recreate on observation timeout. Inspect existing jobs before retrying
installation. Remote job logs and explicit exit files are in
`/home/ubuntu/workspace/k1-runtime/`.
Use `brev exec` with the full CLI path above for noninteractive commands.

Preflight found Ubuntu22.04.5/glibc2.35, 144GiB RAM, 104GiB free disk,
L40S46068MiB, driver565.57.01 and Python3.10.12. No simulator packages were installed.
The driver was upgraded to **580.178.04** through NVIDIA's configured apt repository.
Only installed NVIDIA driver holds were released; container tooling was left alone.
The first install failed because `libnvidia-extra-565` owned a file also supplied
by `libnvidia-gl-580`. A reviewed targeted removal and apt repair completed with
exit0. DKMS modules built for both installed kernels, the OS rebooted once, and
`nvidia-smi` verified driver580.178.04 afterward. Failed and repair logs are retained
under local ignored `runs/brev-k1-20261017/` and remotely.

`tools/remote_runtime_install.sh` starts a single detached, logged install of
Python3.11.13, IsaacSim5.1.0, CUDA12.8 Torch2.7.0 and IsaacLab2.3.2
(`37ddf626871758333d6ed89cf64ad702aef127d0`). Its launch marker prevents Brev's
automatic SSH retry from duplicating a mutation. Initial installation needed
the recorded repair/reconciliation scripts: flatdict's legacy build requires
setuptools80.9.0, and newer IPython conflicted with Isaac's psutil pin (8.37.0 used).
`libglu1-mesa` was also missing in the base image and has been installed.

The prepared environment passed a CUDA tensor operation and the real
`tools/isaac_smoke.py` headless falling-cube/RGB test:120physicssteps, final center
height0.249998m, a visible rendered cube, and hashed PNGs. See
`experiments/codex-20261017T1956-isaac-smoke/manifest.json`. The first attempt failed
with empty camera buffers while libGLU was absent; both attempts are retained.
Native Isaac shutdown can returnexit0 after Python errors, so the orchestration
also requires the manifest's explicit success status.

**Dependency limitation:** `pip check` retains one upstream conflict: IsaacLab's
Starlette0.49.1 pin disagrees with IsaacSim's FastAPI0.115.7 requirement (<0.46).
The explicit Lab pin is preserved; no web API service is launched. This is not a
clean dependency-check result. The actual physics/RGB path was tested separately.
See `isaac-runtime-dependency-review.json`, `isaac-pip-check.txt`, and the exact
`isaac-runtime-packages.txt`. The original installed metadata's startup=false is
an installation-time snapshot, superseded by the smoke evidence rather than edited.

The pinned Booster training README reports testing with Isaac Lab **2.3.2** and
Isaac Sim **5.1.0**. Start by reproducing that compatibility baseline. NVIDIA now
marks 5.1.0 unsupported; migration needs an explicit compatibility experiment.
[Requirements](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html)
exclude GPUs without RT cores. The [L40S product page](https://www.nvidia.com/en-us/data-center/l40s/)
lists RT cores; this is a suitable candidate, not proof the VM driver/container works.
Source leads were first collected via You.com in you-brev-isaac-compatibility.json.

Next evidence: official K1 model/controller integration, articulated camera,
payload motion, camera-to-action runs and actual PPO/VLA training.
Record failures and all attempt counts. No PPO/VLA training has been performed yet.

Local lifecycle records are under ignored `runs/brev-k1-20261017/`. The cost guard
helper is available for future explicitly bounded trials, but is not active for
this demo reservation and must not be restarted with its old deadline.
