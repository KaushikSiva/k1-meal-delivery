# GR00T N1.7 real training pilot

**20 actual optimizer updates completed**, followed by saved-checkpoint reload and real recorded-validation-frame inference. This is training feasibility, not a delivery-performance result.

The pinned official GR00T source dac54b313160c201c450f97df0fd74ebd379c892 trained a NEW_EMBODIMENT head-camera/state16/action5 adapter on the same3 episodes/262frames used by SmolVLA. The separate validation episode contains149frames. Conversion to LeRobot v2 preserved every decoded RGB frame byte-for-byte. Horizon10, batch1, learning rate1e−4, dataset seed9301. LLM and vision were frozen; the projector and diffusion action module trained.

The run updated1,620,515,968 trainable parameters;1,523,500,032 frozen parameters retained identical aggregate hashes. Trainable aggregate hash changed. Actual global step20, training runtime27.51s, wall98.86s, peak GPU allocation38,529,214,464bytes. All three saved shard hashes are recorded in manifest.json. Live metrics: [private W&B run](https://wandb.ai/kaushik-siva88/k1-meal-delivery-20261017/runs/groot-pilot-02).

The saved shards were independently hash-checked and loaded through official Gr00tPolicy with strict validation. One recorded validation image/state/text input produced finite action output; first inference0.3995s. This ran zero additional optimizer steps and sent zero actuator commands. No offline quality comparison or closed-loop GR00T trial has run.

Attempt01 failed before training because TorchCodec lacked native FFmpeg libraries. Ubuntu FFmpeg4.4.2 installation and actual87-frame decode fixed that dependency. Reload01 failed because Transformers attempted a Hugging Face metadata query while offline mode was enabled; reload02 used the already authorized Hugging Face access and succeeded. Failures remain on the VM. Saved duplicate checkpoint shards were hash-verified and hardlinked to recover disk space without changing bytes or paths.

Weights remain in `/home/ubuntu/workspace/k1-runtime/evidence/groot-pilot-02/checkpoint`; no weights, videos or credentials are committed. Full manifests and training metrics are included here. Hardware capability and learning benefit are unverified.
