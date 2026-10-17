# GR00T prerequisite status

The user configured Hugging Face access. An authenticated request for the
pinned Cosmos-Reason2-2B configuration returned HTTP 200 on 2026-10-17.
Credentials remain in ignored files and are not part of experiment artifacts.

Official Isaac-GR00T source is pinned to
`dac54b313160c201c450f97df0fd74ebd379c892`. Setup uses its frozen uv lock in a
separate `.venv-groot` environment on the authorized L40S, preserving the
Isaac and SmolVLA environments. The dependency check, import and pinned model
downloads completed with exit zero. See the [setup report](../experiments/codex-20261017T2215-groot-setup/REPORT.md).
No GR00T inference, optimizer update or K1 action has been demonstrated yet.

The model revisions are in `vla-model-lock.json`. The upstream new-embodiment
workflow requires an explicit modality mapping and GR00T's LeRobot v2 data
format. Our bounded navigation subgoals differ from the pretrained manipulation
actions; successful loading alone would not establish compatibility or useful
robot behavior.

Sources: [pinned official installation instructions](https://github.com/NVIDIA/Isaac-GR00T/tree/dac54b313160c201c450f97df0fd74ebd379c892#installation),
[new-embodiment guide](https://github.com/NVIDIA/Isaac-GR00T/blob/dac54b313160c201c450f97df0fd74ebd379c892/getting_started/finetune_new_embodiment.md).
