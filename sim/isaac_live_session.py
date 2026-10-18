"""Interactive Isaac GUI for the actual hand-contact baseline, never pose replay."""
import time
import json
import os
import tempfile
from pathlib import Path
import numpy as np
import torch


def run_live_session(app,sim,robot,payload,handmodel,camera,speed,duration,state_path=None):
    import omni.ui as ui
    from omni.kit.viewport.utility import get_active_viewport
    from isaacsim.core.utils.numpy.rotations import euler_angles_to_quats
    from sim.k1_isaac_policy import IsaacK1Policy
    from sim.k1_hand_carry import ARM_POSE
    dt=sim.get_physics_dt()
    arms=handmodel.arms.tolist()
    hand_targets=torch.tensor([ARM_POSE[robot.joint_names[i]] for i in arms],device='cuda:0')
    state=dict(running=False,reset=False,step=0,follow=True,closed=False)
    state_path=state_path or Path(tempfile.gettempdir())/f'tableside-isaac-{os.getpid()}.json'
    last_write=0.

    def record_state():
        nonlocal last_write
        if state_path is not None and time.monotonic()-last_write>.25:
            state_path.write_text(json.dumps(dict(state,simulated_seconds=state['step']*dt,
                root_xyz=robot.data.root_pos_w[0].cpu().tolist(),
                tray_xyz=payload['tray'].data.root_pos_w[0].cpu().tolist()))+'\n')
            last_write=time.monotonic()

    def make_bridge():
        bridge=IsaacK1Policy(robot,device='cuda:0')
        original=bridge.controller.policy.compute_observation
        def observation():
            data=bridge.controller.robot.data
            ids=[bridge.controller.cfg.robot.joint_names.index(n) for n in ARM_POSE]
            data.joint_pos[ids]=bridge.controller.robot.default_joint_pos[ids].to(data.joint_pos.device)
            data.joint_vel[ids]=0.
            return original()
        bridge.controller.policy.compute_observation=observation
        return bridge

    def start():
        if state['step']*dt>=duration:state['reset']=True
        state['running']=True

    def pause():
        state['running']=False

    def reset():
        state.update(reset=True,running=False)

    def follow():
        state['follow']=not state['follow']

    viewport=get_active_viewport()
    if viewport is not None:viewport.camera_path=camera.prim_path
    window=ui.Window('Tableside — Live Physics',width=370,height=245)
    with window.frame:
        with ui.VStack(spacing=8):
            ui.Label('TABLESIDE | Isaac Sim on Crusoe L40S',height=24)
            ui.Label('Free tray + pizza + Coke supported by hand contact.',word_wrap=True,height=35)
            ui.Label('Scripted walking baseline. No trained VLA/PPO active.',word_wrap=True,height=32)
            with ui.HStack(height=32,spacing=6):
                ui.Button('Start / Resume',clicked_fn=start)
                ui.Button('Pause',clicked_fn=pause)
                ui.Button('Reset',clicked_fn=reset)
            ui.Button('Toggle following camera',clicked_fn=follow,height=28)
            label=ui.Label('Ready — press Start',height=24)
    window.position_x=15;window.position_y=75
    bridge=make_bridge();targets=robot.data.default_joint_pos.clone()
    sim.pause()
    print('TABLESIDE_LIVE_READY',flush=True)
    while app.is_running():
        if state['reset']:
            sim.play()
            robot.write_root_pose_to_sim(robot.data.default_root_state[:,:7])
            robot.write_root_velocity_to_sim(robot.data.default_root_state[:,7:])
            robot.write_joint_state_to_sim(robot.data.default_joint_pos,robot.data.default_joint_vel)
            robot.reset()
            for obj in payload.values():
                obj.write_root_pose_to_sim(obj.data.default_root_state[:,:7])
                obj.write_root_velocity_to_sim(obj.data.default_root_state[:,7:]);obj.reset()
            bridge=make_bridge();targets=robot.data.default_joint_pos.clone()
            state.update(step=0,reset=False)
            if not state['running']:sim.pause()
        if not state['running']:
            if sim.is_playing():sim.pause()
            label.text=f"Paused | {state['step']*dt:.1f} / {duration:.0f} simulated seconds"
            app.update();record_state();time.sleep(.02);continue
        if not sim.is_playing():sim.play()
        step=state['step'];t=step*dt
        if step%10==0:targets=bridge.step((speed if 2<=t<duration-2 else 0.,0.,0.))
        targets[:,arms]=hand_targets
        ff=handmodel.feedforward(robot.data.joint_pos[0].cpu().numpy(),robot.data.joint_vel[0].cpu().numpy(),
            robot.data.root_quat_w[0].cpu().numpy(),robot.data.root_ang_vel_b[0].cpu().numpy())
        robot.set_joint_effort_target(torch.tensor(ff,device='cuda:0',dtype=torch.float32).unsqueeze(0))
        robot.set_joint_position_target(targets);robot.write_data_to_sim()
        render=step%20==19
        if render and state['follow']:
            camera.set_world_pose(position=robot.data.root_pos_w[0].cpu().numpy()+np.array([1.25,-1.15,.55]),
                orientation=euler_angles_to_quats(np.array([0,12,137]),degrees=True))
        sim.step(render=render);robot.update(dt)
        for obj in payload.values():obj.update(dt)
        state['step']+=1
        if render:
            label.text=f"Running physics | {state['step']*dt:.1f} / {duration:.0f} seconds"
            record_state()
        if state['step']*dt>=duration or float(robot.data.root_pos_w[0,2])<.25:
            state['running']=False
