"""Proprioceptive residual interface: no world pose, linear velocity or load truth."""
import numpy as np

OBSERVATION_DIM=65
ACTION_DIM=12
RESIDUAL_BOUND_RAD=.08


def hand_observation(gyro,quaternion,joint_position,joint_velocity,nominal,command,previous):
    arrays=[np.asarray(x,np.float32) for x in
            (gyro,quaternion,joint_position,joint_velocity,nominal,command,previous)]
    shapes=[(3,),(4,),(22,),(22,),(22,),(3,),(12,)]
    if any(x.shape!=shape or not np.isfinite(x).all() for x,shape in zip(arrays,shapes)):
        raise ValueError('Invalid hand-residual sensor inputs')
    gyro,q,pos,vel,nominal,command,previous=arrays
    norm=np.linalg.norm(q)
    if norm<1e-6:raise ValueError('Invalid IMU quaternion')
    w,x,y,z=q/norm
    gravity=np.array([2*(w*y-x*z),-2*(w*x+y*z),-(1-2*(x*x+y*y))],np.float32)
    obs=np.concatenate((gyro,gravity,command,pos-nominal,.1*vel,previous))
    assert obs.shape==(OBSERVATION_DIM,)
    return obs


class HandResidualPolicy:
    def __init__(self,checkpoint):
        import hashlib,json
        from pathlib import Path
        import torch
        from training.ppo_core import ResidualActorCritic
        checkpoint=Path(checkpoint)
        report=json.loads((checkpoint/'manifest.json').read_text())
        path=checkpoint/'final.pt'
        self.sha256=hashlib.sha256(path.read_bytes()).hexdigest()
        if self.sha256!=report['final_checkpoint_sha256']:raise ValueError('Hand checkpoint hash mismatch')
        self.model=ResidualActorCritic(OBSERVATION_DIM,ACTION_DIM)
        self.model.load_state_dict(torch.load(path,map_location='cpu',weights_only=True)['model'],strict=True)
        self.model.eval();self.torch=torch;self.report=report

    def action(self,observation):
        obs=np.asarray(observation,np.float32)
        if obs.shape!=(OBSERVATION_DIM,) or not np.isfinite(obs).all():raise ValueError('Invalid residual observation')
        with self.torch.inference_mode():
            action=RESIDUAL_BOUND_RAD*self.torch.tanh(self.model.actor(self.torch.from_numpy(obs).unsqueeze(0)))
        value=action[0].numpy()
        if not np.isfinite(value).all():raise ValueError('Invalid residual output')
        return value
