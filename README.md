# K1 meal delivery

Vision-guided Booster K1 meal delivery with explicit memory, search, real policy training and measured progress toward hardware deployment.

**Current state:** the official unloaded K1 walking policy runs in CPU MuJoCo; a 15-second diagnostic reproduced exactly but showed poor command tracking. The reviewed autonomy baseline passes 34 synthetic software tests after fixes for localization, stale observations and motion limits; camera/control integration remains pending. No integrated vision-guided delivery, project training or physical robot result exists yet. A Crusoe L40S is provisioning through Brev; hardware remains unavailable.

- [Goal and acceptance requirements](GOAL.md)
- [Team instructions](AGENTS.md)
- [Path ownership](coordination/OWNERSHIP.md)
- [Codex status](coordination/CODEX_STATUS.md) / [Claude status](coordination/CLAUDE_STATUS.md)
- [Initial Claude prompt](coordination/CLAUDE_START.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Milestones](docs/ROADMAP.md)
- [Experiment protocol](docs/EVALUATION.md)
- [Resources and access](docs/RESOURCES.md)
- [Run the K1 MuJoCo diagnostic](sim/README.md)

CPU autonomy test setup (Python 3.12):

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest tests/autonomy -q -p no:cacheprovider
python3 -m unittest discover -s tests/integration -v
python3 -m unittest discover -s tests/evaluation -v
```

Use the explicit interpreter paths: the shell's `python3` may not have the test
dependencies. Do not recreate an environment while another process is using it.

Private remote: https://github.com/KaushikSiva/k1-meal-delivery

Local workspace: `/Users/kaushiksivakumar/workspace/k1-meal-delivery`.

Read the per-agent status files for current work; this README is not a live performance dashboard.
