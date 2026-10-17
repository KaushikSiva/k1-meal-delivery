"""Verify terminal accounting independently and real gradient updates."""
import torch
from training.ppo_core import advantages,ResidualActorCritic,update


def test_timeout_bootstraps_without_leaking_next_episode():
    r=torch.tensor([[1.,1.],[100.,100.]])
    v=torch.zeros_like(r);nv=torch.tensor([[10.,10.],[0.,0.]])
    terminated=torch.tensor([[True,False],[True,True]])
    done=torch.ones_like(terminated)
    a,ret=advantages(r,v,nv,terminated,done,gamma=.9,lam=1.)
    torch.testing.assert_close(a,torch.tensor([[1.,10.],[100.,100.]]))
    torch.testing.assert_close(ret,a)


def test_ppo_changes_real_weights_and_zero_mean_starts_as_baseline():
    torch.manual_seed(7);m=ResidualActorCritic();obs=torch.randn(8,4,89)
    assert torch.count_nonzero(m.actor(obs))==0
    with torch.no_grad():act,lp,v=m.sample(obs)
    old=[p.detach().clone() for p in m.parameters()]
    result=update(m,torch.optim.Adam(m.parameters(),lr=3e-4),obs,act,lp,v+1,torch.randn(8,4),epochs=2,minibatch=16)
    assert result['optimizer_steps']==4
    assert any(not torch.equal(a,b) for a,b in zip(old,m.parameters()))
    assert all(torch.isfinite(p).all() for p in m.parameters())
