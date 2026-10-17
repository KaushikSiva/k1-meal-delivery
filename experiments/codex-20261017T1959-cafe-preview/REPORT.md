# Café development render — attempt 02

Real IsaacSim5.1/L40S environment preview: four1280×720 images and90physicssteps. No robot, navigation, training, or delivery result. All downloaded PNG hashes match the remote manifest.

The preceding attempt01 failed with empty camera buffers and missinglibGLU. After installinglibglu1-mesa, the separate falling-cube physics/RGB smoke passed (120steps,z0.249998m), then this scene rendered.

Visual review found a missing ceiling and imported furniture rendering red rather than its source PBR textures. These frames are retained as a development result, not the final presentation scene. A third attempt repairs material binding and encloses the ceiling.

Source archive: `runs/brev-k1-20261017/preview-02-source.tar.gz` (local ignored artifact). SceneUSD is retained remotely at `/home/ubuntu/workspace/k1-runtime/evidence/cafe-02/cafe.usda` on `k1-isaac-check-20261017`; its200970657bytes and hash are in the manifest. It is not in Git.

Furniture, textures and HDRI: [Poly Haven](https://polyhaven.com/), CC0; exact asset lock in `sim/cafe_assets.json`.
