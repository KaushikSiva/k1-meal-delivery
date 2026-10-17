"""Real pinned actor + shuffled Isaac telemetry interface; no physics claims."""
from pathlib import Path
from types import SimpleNamespace
import pytest

torch=pytest.importorskip('torch')
from sim.k1_isaac_policy import IsaacK1Policy, BaseController, K1WalkTaskCfg, DEPLOY
pytestmark=pytest.mark.skipif(not (DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt').exists(),reason='pinned actor absent')


def test_shuffled_isaac_joints_match_official_actor_and_ignore_world_truth():
    cfg=K1WalkTaskCfg()
    cfg.policy.checkpoint_path=str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt')
    reference=BaseController(cfg);reference.start()
    order=list(range(21,-1,-1))
    q=torch.tensor(cfg.robot.default_joint_pos)+torch.linspace(-.03,.04,22)
    qd=torch.linspace(-.15,.2,22)
    quat=torch.tensor([.99875026,0.,0.,.04997917])
    gyro=torch.tensor([.02,-.03,.04])
    data=SimpleNamespace(joint_pos=q[order][None].clone(),joint_vel=qd[order][None].clone(),
        root_quat_w=quat[None],root_ang_vel_b=gyro[None],root_pos_w=torch.tensor([[999.,999.,999.]]),
        root_lin_vel_b=torch.tensor([[999.,999.,999.]]))
    robot=SimpleNamespace(joint_names=[cfg.robot.joint_names[i] for i in order],data=data)
    bridge=IsaacK1Policy(robot)
    for _ in range(3):
        d=reference.robot.data
        d.joint_pos.copy_(q);d.joint_vel.copy_(qd);d.root_quat_w.copy_(quat);d.root_ang_vel_b.copy_(gyro)
        reference.vel_command.lin_vel_x=.35
        expected=reference.policy_step()[order]
        actual=bridge.step((.35,0,0))[0]
        torch.testing.assert_close(actual,expected,rtol=1e-6,atol=1e-6)
        torch.testing.assert_close(bridge.controller.policy.obs_history,reference.policy.obs_history)
    robot.joint_names[-1]=robot.joint_names[0]
    with pytest.raises(ValueError,match='unique'):
        IsaacK1Policy(robot)
