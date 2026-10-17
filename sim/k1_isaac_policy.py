"""Name-mapped single-robot Isaac bridge to the unchanged pinned K1 actor.

Only joint encoders, quaternion/gyro telemetry and requested velocity enter the
actor. World position/linear velocity are deliberately absent. Not training.
"""
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT/'sim/vendor/booster_deploy'
sys.path.insert(0,str(DEPLOY))
from booster_deploy.controllers.base_controller import BaseController
from tasks.locomotion.robots.k1 import K1WalkTaskCfg


class IsaacK1Policy:
    def __init__(self, articulation, device='cpu'):
        self.articulation = articulation
        cfg = K1WalkTaskCfg()
        cfg.policy.device = device
        cfg.policy.checkpoint_path = str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt')
        real_names = cfg.robot.joint_names
        sim_names = list(articulation.joint_names)
        if len(sim_names)!=len(real_names) or set(sim_names)!=set(real_names):
            raise ValueError('Isaac joint names must match all 22 unique official K1 joints')
        if articulation.data.joint_pos.shape != (1,22):
            raise ValueError('This diagnostic bridge supports exactly one K1')
        self.controller = BaseController(cfg)
        self.real_from_sim = torch.tensor([sim_names.index(n) for n in real_names],device=device)
        self.sim_from_real = torch.tensor([real_names.index(n) for n in sim_names],device=device)
        self.device=device
        self.controller.start()

    def step(self, velocity_command):
        if len(velocity_command)!=3 or not all(torch.isfinite(torch.tensor(float(x))) for x in velocity_command):
            raise ValueError('Velocity command must contain three finite values')
        src=self.articulation.data
        dst=self.controller.robot.data
        dst.joint_pos.copy_(src.joint_pos[0].to(self.device)[self.real_from_sim])
        dst.joint_vel.copy_(src.joint_vel[0].to(self.device)[self.real_from_sim])
        dst.root_quat_w.copy_(src.root_quat_w[0].to(self.device))
        dst.root_ang_vel_b.copy_(src.root_ang_vel_b[0].to(self.device))
        cmd=self.controller.vel_command
        cmd.lin_vel_x,cmd.lin_vel_y,cmd.ang_vel_yaw=map(float,velocity_command)
        targets=self.controller.policy_step()
        if not self.controller.is_running:
            raise RuntimeError('Upstream K1 actor fall fallback triggered')
        if not torch.isfinite(targets).all():
            raise RuntimeError('K1 actor returned nonfinite targets')
        return targets[self.sim_from_real].unsqueeze(0).to(src.joint_pos.device)

    def reset(self):
        self.controller.start()
