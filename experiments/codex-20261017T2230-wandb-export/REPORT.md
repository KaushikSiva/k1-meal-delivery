# Historical training evidence uploaded to W&B

Completed 2026-10-17. This imports the already completed real PPO02 and SmolVLA02
training logs; the export itself performs no optimization. Both runs were remotely
verified `finished`, in a project verified `PRIVATE` before any upload.

- [PPO02, 100 iteration rows / 1,600 optimizer updates](https://wandb.ai/kaushik-siva88/k1-meal-delivery-20261017/runs/k1-ppo-02-historical)
- [SmolVLA02, 200 optimizer update rows](https://wandb.ai/kaushik-siva88/k1-meal-delivery-20261017/runs/smolvla-train-02-historical)

Configs preserve original source/dataset/checkpoint hashes, original timestamps,
training budget and limits. Evidence artifacts contain only the exact manifest and
metrics files. No weights, credentials or automatic code snapshots were uploaded.
The logged wall-clock upload date must not be interpreted as the training time;
original timing remains in each manifest/config. GR00T has no training run yet.

Reproducible importer: `tools/export_wandb_runs.py`, W&B SDK 0.27.2.
Remote receipt: `/home/ubuntu/workspace/k1-runtime/evidence/wandb-export-01/receipt.json`.
Local receipt records original evidence hashes and URLs. Future training still
needs live logging integration; this checkpoint establishes historical exports.
