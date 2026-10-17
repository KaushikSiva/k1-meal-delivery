"""Compare vectorized observations/history/targets to actual pinned controller."""
from types import SimpleNamespace
import torch
from sim.k1_isaac_policy import BaseController,K1WalkTaskCfg,DEPLOY
from sim.k1_batch_policy import BatchedK1Policy


def test_batch_matches_upstream_through_history_and_selective_reset():
    torch.manual_seed(12)
    cfg=K1WalkTaskCfg();cfg.policy.checkpoint_path=str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt')
    names=list(reversed(cfg.robot.joint_names));order=[cfg.robot.joint_names.index(n) for n in names]
    refs=[BaseController(cfg) for _ in range(3)]
    for r in refs:r.start()
    batched=BatchedK1Policy(names,3)
    commands=torch.tensor([[.35,0.,0.],[.2,.1,-.2],[0.,0.,.1]])
    for step in range(6):
        if step==3:batched.reset(torch.tensor([1]));refs[1].start()
        q=torch.tensor(cfg.robot.default_joint_pos)[None,:]+torch.randn(3,22)*.02
        qd=torch.randn(3,22)*.1;gyro=torch.randn(3,3)*.03
        quat=torch.randn(3,4)*.02;quat[:,0]=1.;quat/=quat.norm(dim=-1,keepdim=True)
        data=SimpleNamespace(joint_pos=q[:,order],joint_vel=qd[:,order],root_ang_vel_b=gyro,root_quat_w=quat)
        expected=[]
        for i,r in enumerate(refs):
            r.robot.data.joint_pos.copy_(q[i]);r.robot.data.joint_vel.copy_(qd[i])
            r.robot.data.root_quat_w.copy_(quat[i]);r.robot.data.root_ang_vel_b.copy_(gyro[i])
            r.vel_command.lin_vel_x,r.vel_command.lin_vel_y,r.vel_command.ang_vel_yaw=commands[i].tolist()
            expected.append(r.policy_step()[order])
        actual=batched.step(data,commands)
        torch.testing.assert_close(actual,torch.stack(expected),rtol=1e-5,atol=2e-6)
        torch.testing.assert_close(batched.history,torch.stack([r.policy.obs_history for r in refs]),rtol=1e-5,atol=2e-6)
