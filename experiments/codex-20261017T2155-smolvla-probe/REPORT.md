# SmolVLA loads and backpropagates on the L40S

The pinned public SmolVLA checkpoint passed a GPU compatibility probe with
our proposed 16-dimensional state, five-dimensional action and one head RGB
camera. **There were zero optimizer updates. This was not VLA fine-tuning.**
Inputs and targets were synthetic tensors; no robot was actuated and no model
weights were saved.

The isolated Python 3.12.12 environment uses LeRobot 0.6.1 and PyTorch
2.9.0+cu128. Dependency checking passed. Setup first failed on the default
Python 3.10 and then its missing ensurepip; the successful third setup used
portable Python via uv without changing the Isaac environment.
Exact package versions, downloaded file hashes and pinned model revisions
are recorded in `setup/manifest.json` and `setup/requirements.freeze.txt`.

| GPU measurement | Result |
| --- | ---: |
| Parameters loaded strictly | 450,046,176 |
| Parameters allowing gradients | 99,880,992 |
| Model load | 13.37 s |
| Action chunk shape | 1 × 10 × 5 |
| First inference | 451 ms |
| Three warm inferences | 138, 136, 136 ms |
| Peak allocated GPU memory, inference | 1.265 GB |
| Peak allocated GPU memory, backward | 1.458 GB |
| Synthetic loss / gradient norm | 0.2721 / 17.90 |
| Optimizer updates | 0 |

Finite outputs and gradients establish compatibility only. These timings
exclude sensor capture, preprocessing and downstream navigation, and are not
a deployed latency benchmark. Training data collection, actual updates,
checkpoint comparison and held-out robot evaluation remain outstanding.

Probe source SHA256:
`d9b433aed1b50627c47d12c433367ada667dba39d235252e5b4603cb467cbb7c`.
The source snapshot is retained in
`runs/brev-k1-20261017/smolvla-probe-01-source.tar.gz`; remote evidence is at
`/home/ubuntu/workspace/k1-runtime/evidence/smolvla-probe-01` and
`evidence/smolvla-setup-03`. Model weights remain outside Git.
