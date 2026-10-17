# VLA prerequisite check

Status: pinned models downloaded and GPU shape/gradient probe passed,
**no K1 VLA fine-tuning yet**. See the [actual probe report](../experiments/codex-20261017T2155-smolvla-probe/REPORT.md).
The genuine PPO carrying updates are a separate model and training objective.

Official model revisions and access flags are pinned in vla-model-lock.json.
The public SmolVLA checkpoint and its SmolVLM2 backbone were accessible without
authentication. Both list Apache-2.0 in their model metadata. The source config
uses six-dimensional state/action features padded internally to 32, three image
keys, and action chunks of 50. Our proposed 16-dimensional state, five-dimensional
subgoal and one-camera interface therefore require explicit configuration,
normalization and measured input/output checks before training or deployment.

The completed setup is an isolated Python 3.12.12 environment on the authorized
L40S, LeRobot 0.6.1, PyTorch 2.9.0/CUDA 12.8, torchvision 0.24.0 and torchcodec
0.8.0. tools/remote_smolvla_setup.sh pins those requested versions, checks installed
dependencies, downloads pinned snapshots, and hashes the files. It does not run
training or command the robot. Setup03 exited zero, dependency checking passed,
and the downloaded models were recorded with per-file hashes in its manifest.

Setup01 stopped before installation because the VM's default Python was 3.10.12.
Setup02 stopped because the system Python lacks ensurepip. Setup03 installs uv
with pip's explicit `--target` into a separate tools directory, then provisions
Python 3.12.12 and the isolated VLA environment. It uses the existing pip executable
without installing packages into the Isaac environment. Logs/PID/exit files are
under `/home/ubuntu/workspace/k1-runtime/smolvla-setup-0{1,2,3}.*`.

GR00T remains a candidate. Its official setup instructions require access to the
gated Cosmos-Reason2-2B backbone. We independently verified the gate through the
Hugging Face API and found no configured local or remote Hugging Face credential.
The user supplied a credential later in the session. An authenticated request for
the pinned gated backbone config returned HTTP 200. Isolated GR00T setup is now
running; that access check alone does not establish a downloaded or usable model.
The GR00T repository and model card disagree about release/license wording, so
we retain the exact sources rather than treating the metadata as resolved.

Sources: [SmolVLA model/config](https://huggingface.co/lerobot/smolvla_base),
[LeRobot 0.6.1 metadata](https://pypi.org/project/lerobot/0.6.1/),
[GR00T installation](https://github.com/NVIDIA/Isaac-GR00T#installation),
[GR00T model card](https://huggingface.co/nvidia/GR00T-N1.7-3B).

The pinned policy loaded strictly on the L40S. A synthetic probe produced finite
1 × 10 × 5 actions and nonzero finite gradients, with 1.458 GB peak allocated
GPU memory during backward. It performed zero optimizer updates.

Next evidence gates: collect valid sensor-only demonstrations; run real updates
with weight-change evidence; evaluate separately
on held-out layouts against the executive-only baseline. A failed teacher trial
must not be relabeled a successful delivery demonstration.
