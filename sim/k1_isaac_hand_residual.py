"""Name-mapped proprioceptive hand PPO adapter for Isaac joint targets."""
import numpy as np
import torch
from deployment.hand_residual import hand_observation,RESIDUAL_BOUND_RAD


class IsaacHandResidual:
    def __init__(self,articulation,baseline,policy):
        self.articulation=articulation;self.policy=policy
        names=list(policy.report['all_joint_names'])
        sim_names=list(articulation.joint_names)
        base_names=list(baseline.controller.cfg.robot.joint_names)
        if len(names)!=22 or len(set(names))!=22 or set(names)!=set(sim_names) or set(names)!=set(base_names):
            raise ValueError('Residual joint contract does not match Isaac and baseline')
        legs=policy.report['leg_joint_names']
        if len(legs)!=12 or len(set(legs))!=12 or not set(legs)<=set(names):
            raise ValueError('Invalid residual leg joint contract')
        if any('head' in n or 'shoulder' in n or 'elbow' in n for n in legs):
            raise ValueError('Residual may only control legs')
        self.sensor_order=[sim_names.index(n) for n in names]
        self.leg_order=[sim_names.index(n) for n in legs]
        self.nominal=baseline.controller.robot.default_joint_pos.detach().cpu().numpy()[[base_names.index(n) for n in names]]
        self.reset()

    def reset(self):
        self.previous=np.zeros(12,np.float32);self.steps=0;self.max_abs_residual=0.

    def apply(self,targets,command):
        data=self.articulation.data
        cpu=lambda x:x.detach().cpu().numpy()
        obs=hand_observation(cpu(data.root_ang_vel_b[0]),cpu(data.root_quat_w[0]),
            cpu(data.joint_pos[0])[self.sensor_order],cpu(data.joint_vel[0])[self.sensor_order],
            self.nominal,command,self.previous)
        residual=self.policy.action(obs)
        if residual.shape!=(12,) or not np.isfinite(residual).all() or np.abs(residual).max()>RESIDUAL_BOUND_RAD+1e-6:
            raise RuntimeError('Invalid learned hand residual')
        result=targets.clone()
        result[0,self.leg_order]+=torch.as_tensor(residual,device=result.device,dtype=result.dtype)
        self.previous=residual.copy();self.steps+=1
        self.max_abs_residual=max(self.max_abs_residual,float(np.abs(residual).max()))
        return result
