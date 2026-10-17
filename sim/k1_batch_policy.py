"""Batched equivalent of pinned official K1 inference; weights remain frozen.

All observations are deployable joint/IMU/command signals. World position,
linear velocity and payload truth are absent. Tests compare with upstream.
"""
import torch
from sim.k1_isaac_policy import K1WalkTaskCfg, DEPLOY
from booster_deploy.utils.isaaclab.math import quat_apply_inverse


class BatchedK1Policy:
    def __init__(self, joint_names, num_envs, device='cpu'):
        cfg=K1WalkTaskCfg();self.cfg=cfg;self.device=device
        if len(joint_names)!=22 or set(joint_names)!=set(cfg.robot.joint_names):
            raise ValueError('Expected 22 unique official joints')
        self.policy_indices=torch.tensor([joint_names.index(n) for n in cfg.policy.policy_joint_names],device=device)
        self.default=torch.tensor([cfg.robot.default_joint_pos[cfg.robot.joint_names.index(n)] for n in joint_names],device=device)
        self.elbow=joint_names.index(cfg.policy.arm_action_fix_joint_name)
        self.model=torch.jit.load(str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt'),map_location=device).actor.eval()
        for p in self.model.parameters():p.requires_grad_(False)
        self.history=torch.zeros(num_envs,10,69,device=device)
        self.last_action=torch.zeros(num_envs,20,device=device)
        self.filtered=self.default.repeat(num_envs,1)
        self.fresh=torch.ones(num_envs,dtype=torch.bool,device=device)
        self.gravity=torch.tensor([0.,0.,-1.],device=device).repeat(num_envs,1)

    def observe(self,data,commands):
        ids=self.policy_indices
        return torch.cat((data.root_ang_vel_b,quat_apply_inverse(data.root_quat_w,self.gravity),
            commands,data.joint_pos[:,ids]-self.default[ids],data.joint_vel[:,ids]*.1,self.last_action),dim=-1).clamp(-100,100)

    @torch.no_grad()
    def step(self,data,commands):
        obs=self.observe(data,commands)
        self.history=torch.roll(self.history,-1,dims=1)
        self.history[:,-1]=obs
        self.history[self.fresh]=obs[self.fresh,None,:].repeat(1,10,1)
        self.fresh.zero_()
        action=self.model(self.history.flatten(1)).clamp(-100,100)
        if action.shape!=self.last_action.shape or not torch.isfinite(action).all():
            raise RuntimeError('Invalid batched actor output')
        self.last_action.copy_(action)
        target=self.default.repeat(len(action),1)
        target[:,self.policy_indices]+=action*.25
        target[:,self.elbow]-=.2*.25
        self.filtered.lerp_(target,.8)
        return self.filtered.clone()

    def reset(self,ids):
        self.history[ids]=0;self.last_action[ids]=0
        self.filtered[ids]=self.default;self.fresh[ids]=True
