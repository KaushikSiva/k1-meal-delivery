"""Actual free hand-contact MuJoCo rollouts with deployable residual observations.

True velocity, height and payload positions are reward/termination signals only.
The frozen walking actor and torque-limited arm controller remain in the loop.
"""
from pathlib import Path
import numpy as np
import torch
from sim.k1_hand_carry import make_model,ARM_POSE
from sim.k1_hand_controller import HandSensorController
from sim.k1_observation import sensor_spec
from sim.run_k1_baseline import K1WalkTaskCfg,DEPLOY
from deployment.hand_residual import hand_observation,RESIDUAL_BOUND_RAD


class HandCarryEnv:
    def __init__(self,workdir,seed=9801):
        self.root=Path(workdir);self.root.mkdir(parents=True,exist_ok=True)
        self.xml=self.root/'hand.xml';make_model(self.xml,handle_seats=True)
        self.rng=np.random.default_rng(seed);self.seed=seed
        self.cfg=K1WalkTaskCfg();self.cfg.mujoco.log_states=None
        self.cfg.policy.checkpoint_path=str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt')
        self.commands=np.array([[0,0,0],[0,0,-.15],[0,0,.15],[0,0,-.25],[0,0,.25],
                                [.4,0,0],[.4,0,-.15],[.4,0,.15]],float)
        self.ctrl=None

    def reset(self,command=None,yaw=None):
        command=self.commands[self.rng.integers(len(self.commands))] if command is None else command
        yaw=float(self.rng.uniform(-.2,.2)) if yaw is None else yaw
        self.motion_command=np.asarray(command,float)
        self.ctrl=HandSensorController(self.cfg,sensor_spec(self.xml),start=(0.,0.,yaw),seed=self.seed,head_pitch=-.2)
        self.ctrl.update_state();self.ctrl.start()
        self.previous=np.zeros(12,np.float32);self.steps=0
        self.legs=np.array([i for i,n in enumerate(self.cfg.robot.joint_names)
                            if n not in ARM_POSE and 'head' not in n])
        assert len(self.legs)==12
        return self.observe()

    def command(self):
        return self.motion_command.copy() if 100<=self.steps<300 else np.zeros(3)

    def observe(self):
        c=self.ctrl;d=c.mj_data
        return hand_observation(d.qvel[3:6],d.qpos[3:7],d.qpos[c.qi],d.qvel[c.vi],
                                c.robot.default_joint_pos.numpy(),self.command(),self.previous)

    def step(self,residual):
        residual=np.asarray(residual,np.float32)
        if residual.shape!=(12,) or not np.isfinite(residual).all() or np.abs(residual).max()>RESIDUAL_BOUND_RAD+1e-6:
            raise ValueError('Invalid bounded leg residual')
        c=self.ctrl;d=c.mj_data;command=self.command()
        c.vel_command.lin_vel_x,c.vel_command.lin_vel_y,c.vel_command.ang_vel_yaw=command
        c.update_state();target=c.policy_step().clone()
        target[self.legs]+=torch.from_numpy(residual)
        c.ctrl_step(target);self.steps+=1
        # Privileged simulator state below is restricted to reward/termination.
        R=d.xmat[c.mj_model.body('trunk').id].reshape(3,3)
        velocity=R.T@d.qvel[:3]
        desired=.5*command[:2]  # measured nominal forward tracking prior
        tracking=float(np.exp(-np.sum((velocity[:2]-desired)**2)/.04))
        turning=float(np.exp(-(d.qvel[5]-command[2])**2/.04))
        tilt=float(np.arccos(np.clip(R[2,2],-1,1)))
        shifts=np.asarray(c.payload_rows[-1][-2:])
        rate=float(np.sum((residual-self.previous)**2))
        reward=1.5*tracking+.75*turning+.25-4*tilt**2-40*float(np.sum(shifts**2))-.1*rate
        terminated=bool(d.qpos[2]<.32 or tilt>np.pi/4 or c.hand_metrics['payload_drop'] or not c.is_running)
        if terminated:reward-=10.
        done=terminated or self.steps>=400
        self.previous=residual.copy()
        info=dict(tracking=tracking,turning=turning,tilt_rad=tilt,
                  speed_m_s=float(np.linalg.norm(d.qvel[:2])),payload_shift_m=float(shifts.max()),
                  terminated=terminated,command=command.tolist())
        return self.observe(),float(reward),terminated,done,info
