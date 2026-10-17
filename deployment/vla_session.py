"""Single follower ownership with delayed, bounded VLA proposals in simulation.

Synchronous model calls pause wall-clock simulation, but their measured latency
is also applied as simulated proposal-delivery delay. This is not a real-time
hardware runtime. The executive/follower continues during simulated delay.
"""
from collections import Counter
import numpy as np
from autonomy.contracts import CommandKind
from autonomy.session import AutonomySession
from vla.adapter import BoundedActionAdapter, EXECUTIVE_ONLY
from vla.inputs import build_inputs


class SelectingFollower:
    def __init__(self, follower, executive, policy, inference_period_s=.5):
        self.base=follower;self.executive=executive;self.policy=policy
        self.adapter=BoundedActionAdapter();self.period=inference_period_s
        self.obs=None;self.new_observation=False;self.next_inference=0.
        self.pending=None;self.active=None;self.calls=[];self.control=[]

    @property
    def v(self):return self.base.v

    def observe(self,obs):
        if obs is not None:
            obs.assert_deployable();self.obs=obs;self.new_observation=True

    def step(self,cmd,pose,now,dt):
        ex=self.executive
        if self.pending is not None and now+1e-9>=self.pending[0]:
            self.active=self.pending[1];self.pending=None
        if (cmd is not None and self.new_observation and now+1e-9>=self.next_inference
                and ex.state not in EXECUTIVE_ONLY and cmd.kind!=CommandKind.STOP):
            self.next_inference=now+self.period
            try:
                p=self.policy.propose(build_inputs(self.obs,ex))
                if p is None:raise ValueError('No proposal returned')
                delay=float(p.latency_s)
                if not np.isfinite(delay) or delay<0:raise ValueError('Invalid inference delay')
                self.pending=(now+delay,p)
                self.calls.append({'t':now,'observation_t':p.timestamp,'latency_s':delay,
                    'available_at':now+delay,'first_action':np.atleast_2d(p.actions)[0].tolist()})
            except Exception as exc:
                self.calls.append({'t':now,'error':f'{type(exc).__name__}: {exc}'})
        self.new_observation=False
        selected=cmd;reason='no executive command'
        if cmd is not None and self.obs is not None:
            proposal=self.active
            # The executive updates only on camera ticks. Use the control clock
            # too, so that a 50Hz tick cannot extend the adapter's 0.6s deadline.
            expired=proposal is not None and now-proposal.timestamp>self.adapter.max_age_s
            selected=self.adapter.select(ex,cmd,self.obs,None if expired else proposal)
            reason='proposal expired on control clock' if expired else self.adapter.decisions[-1].reason
        selected_by=selected.selected_by if selected is not None else 'executive'
        self.control.append({'t':now,'selected_by':selected_by,'reason':reason})
        return self.base.step(selected,pose,now,dt)

    def summary(self):
        latencies=[c['latency_s'] for c in self.calls if 'latency_s' in c]
        return {'inference_calls':len(self.calls),'inference_failures':sum('error' in c for c in self.calls),
            'control_ticks_by_owner':dict(Counter(c['selected_by'] for c in self.control)),
            'decision_reasons':dict(Counter(c['reason'] for c in self.control)),
            'latency_s':{'min':min(latencies),'max':max(latencies),'mean':float(np.mean(latencies))} if latencies else None,
            'timing':'measured synchronous inference delay applied to simulated proposal availability',
            'hardware_runtime':False}


class BoundedVLASession(AutonomySession):
    def __init__(self,*args,proposal_policy,**kwargs):
        super().__init__(*args,**kwargs)
        self.follower=SelectingFollower(self.follower,self.executive,proposal_policy)

    def tick(self,obs,now,dt,feedback=None):
        self.follower.observe(obs)
        return super().tick(obs,now,dt,feedback)
