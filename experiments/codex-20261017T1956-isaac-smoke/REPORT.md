# L40S Isaac Sim physics/RGB smoke — attempt02

Passed a real headless IsaacSim5.1.0 test on NVIDIA L40S driver580.178.04. A0.5m cube drops under physics onto a plane and is rendered by an actual camera.120physicssteps; final center height0.249998m; final speed0.04596m/s (below the provisional0.05smoke threshold);142373red pixels in the final image. This is runtime readiness only, not K1, carrying, training or delivery evidence.

The first attempt failed with empty image buffers and missinglibGLU. Installinglibglu1-mesa fixed the missing graphics dependency. Startup for this successful run took149.33s including first shader compilation; do not interpret that as steady-state simulator throughput.

All downloaded images and positions match manifest hashes. Rawpositions.json stays local and ignored. Source archive: `runs/brev-k1-20261017/preview-02-source.tar.gz`. Failed attempt manifests/logs are retained in `runs/brev-k1-20261017/runtime-audit/` and on the VM.
