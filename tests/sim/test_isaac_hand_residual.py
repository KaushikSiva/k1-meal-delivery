"""Check encoder ordering and leg-only application across simulator joint orders."""
from types import SimpleNamespace as NS
import numpy as np
import torch
import pytest
from sim.k1_isaac_hand_residual import IsaacHandResidual


def test_joint_permutation_preserves_physical_arm_inputs_and_targets():
    names=['head0','head1']+[f'arm{i}' for i in range(8)]+[f'leg{i}' for i in range(12)]
    sim_names=list(reversed(names))
    class Policy:
        report=dict(all_joint_names=names,leg_joint_names=names[-12:])
        def action(self,obs):
            self.obs=obs.copy()
            return np.arange(12,dtype=np.float32)*.001
    policy=Policy()
    data=NS(joint_pos=torch.tensor([[names.index(n)/100 for n in sim_names]]),
            joint_vel=torch.zeros(1,22),root_ang_vel_b=torch.zeros(1,3),
            root_quat_w=torch.tensor([[1.,0.,0.,0.]]))
    articulation=NS(joint_names=sim_names,data=data)
    baseline=NS(controller=NS(cfg=NS(robot=NS(joint_names=names)),robot=NS(default_joint_pos=torch.zeros(22))))
    adapter=IsaacHandResidual(articulation,baseline,policy)
    targets=torch.zeros(1,22);out=adapter.apply(targets,[.4,0,0])
    np.testing.assert_allclose(policy.obs[9:31],np.arange(22)/100,atol=1e-7)
    for i,n in enumerate(names[-12:]):assert float(out[0,sim_names.index(n)])==pytest.approx(i*.001)
    for n in names[:10]:assert out[0,sim_names.index(n)]==0
    assert targets.count_nonzero()==0 and adapter.steps==1
    adapter.reset();assert adapter.steps==0 and not adapter.previous.any()


def test_non_leg_checkpoint_contract_is_rejected():
    names=['head']+[f'leg{i}' for i in range(21)]
    a=NS(joint_names=names)
    b=NS(controller=NS(cfg=NS(robot=NS(joint_names=names))))
    p=NS(report=dict(all_joint_names=names,leg_joint_names=names[:12]))
    with pytest.raises(ValueError,match='only control legs'):IsaacHandResidual(a,b,p)
