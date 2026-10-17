from types import SimpleNamespace
import numpy as np
from autonomy.contracts import AutonomyCommand,CommandKind,Pose2D
from autonomy.executive import State
from deployment.vla_session import SelectingFollower
from vla.adapter import VLAProposal
from vla.action_space import encode,LocalSubgoal


class Follower:
    def __init__(self):self.v=np.zeros(3);self.commands=[]
    def step(self,cmd,pose,now,dt):self.commands.append(cmd);return self.v.copy()


def setup(monkeypatch,delay=.2):
    monkeypatch.setattr('deployment.vla_session.build_inputs',lambda obs,ex:{'timestamp':obs.timestamp})
    ex=SimpleNamespace(now=0.,state=State.APPROACH)
    def propose(inputs):
        return VLAProposal(encode(LocalSubgoal(0,0,0,0,True)),inputs['timestamp'],'fake',delay)
    follower=Follower();selector=SelectingFollower(follower,ex,SimpleNamespace(propose=propose))
    obs=SimpleNamespace(timestamp=0.,pose=SimpleNamespace(pose=Pose2D(0,0,0)),assert_deployable=lambda:None)
    selector.observe(obs)
    cmd=AutonomyCommand(CommandKind.HOLD,0.,10.,selected_by='executive')
    return ex,follower,selector,cmd


def test_measured_delay_and_single_actuation_step(monkeypatch):
    ex,base,s,cmd=setup(monkeypatch)
    for now in [0.,.1,.2]:
        ex.now=now;s.step(cmd,Pose2D(0,0,0),now,.02)
    assert len(base.commands)==3
    assert [c.selected_by for c in base.commands]==['executive','executive','vla']


def test_control_clock_expires_proposal_even_without_new_camera(monkeypatch):
    ex,base,s,cmd=setup(monkeypatch)
    s.step(cmd,Pose2D(0,0,0),0.,.02)
    ex.now=.2;s.step(cmd,Pose2D(0,0,0),.2,.02)
    assert base.commands[-1].selected_by=='vla'
    # Executive timestamp deliberately stays at .2 while the control clock advances.
    s.step(cmd,Pose2D(0,0,0),.62,.02)
    assert base.commands[-1].selected_by=='executive'
    assert s.control[-1]['reason']=='proposal expired on control clock'


def test_safety_state_preempts_available_vla(monkeypatch):
    ex,base,s,cmd=setup(monkeypatch)
    s.step(cmd,Pose2D(0,0,0),0.,.02)
    ex.state=State.SETTLE;ex.now=.2
    s.step(cmd,Pose2D(0,0,0),.2,.02)
    assert base.commands[-1].selected_by=='executive'
    assert 'executive-only state' in s.control[-1]['reason']
