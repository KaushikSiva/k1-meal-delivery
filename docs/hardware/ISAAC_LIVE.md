# Live Isaac Sim desktop

The L40S runs the actual Isaac Sim 5.1 GUI and free hand-contact café scene. Browser input travels through noVNC and an SSH tunnel. This is an interactive physics session, not video playback.

![Browser-connected Isaac GUI after verified Start, Pause and Reset](isaac-live-desktop.png)

On the project Mac, open:

http://localhost:16080/vnc.html?autoconnect=true&resize=scale

The **Tableside — Live Physics** panel is in the upper-left of the Isaac window. Click **Use GR00T**, then **Start / Resume**. GR00T is selected by default when the local model server is configured. The active policy label and inference/accepted-control counters show what is running. **Use baseline** selects the straight-walking demonstration instead.

**Pause** holds the scene; **Reset** restores the robot, free payload, camera and policy history. **Restore robot view** points the viewport back at the robot. **Toggle following camera** allows manual viewport inspection. The panel reopens if closed. The session starts paused and stops after 60 simulated seconds or a detected fall; Start after a reported error resets first.

GR00T N1.7 uses the audited 500-update checkpoint to propose bounded subgoals from the live head RGB-D camera and sensor-estimated pose. The baseline walking actor and arm gravity/load compensation execute checked commands. The optional hand-PPO adapter is not enabled in this launch. This is an experimental interactive session, not a scored delivery trial. The first longer GR00T Isaac run fell at 9.284 simulated seconds after 13 successful inference calls and 271 VLA-selected control ticks. Inference participation is not evidence of successful delivery.

Physics may run slower than wall time over the remote desktop; the panel shows simulated seconds. Reset and stop interventions must be disclosed when presenting short runs. The screenshot above predates the GR00T selector.

Remote services bind only to loopback. The browser link works on the Mac holding the SSH tunnel. Runtime logs are under `/home/ubuntu/workspace/k1-runtime/live-desktop-01/`. `isaac.log` prints `TABLESIDE_LIVE_READY` after the scene and controls are initialized. The VM remains available through the authorized demo window.

Launch the remote desktop with `bash tools/start_isaac_desktop.sh` on the prepared VM. It requires Xvfb, Openbox, x11vnc, noVNC and websockify. The launcher reuses live processes rather than starting duplicates. Forward local TCP16080 to remote loopback6080 over the existing authenticated SSH connection. No VNC port needs public exposure.
