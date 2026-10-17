# GR00T prerequisites downloaded and import-checked

The isolated GR00T environment completed setup on the authorized L40S. Its
dependency check passed, `import gr00t` succeeded, and both pinned GR00T N1.7
and gated Cosmos-Reason2-2B snapshots downloaded. File sizes and hashes are
recorded in `manifest.json`; package versions are in `requirements.freeze.txt`.

The user supplied Hugging Face access after the earlier gate check. Credentials
are excluded from this report and Git. The setup used pinned official source
`dac54b313160c201c450f97df0fd74ebd379c892` and its frozen uv lock in
`/home/ubuntu/workspace/k1-runtime/.venv-groot`, separate from Isaac and SmolVLA.

**No GR00T inference, training update or robot action occurred in this job.**
Next checks are actual model loading, our custom state/action/camera modality
mapping, and measured GPU forward/backward feasibility. A downloaded humanoid
pretrained model does not establish a K1 navigation policy.

Remote metadata: `/home/ubuntu/workspace/k1-runtime/evidence/groot-setup-01`.
Model files: `models/groot_n1_7` and `models/cosmos_reason2` under that runtime.
Setup script: `tools/remote_groot_setup.sh`.
