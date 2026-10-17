#!/usr/bin/env python3
"""Export a trusted project residual checkpoint; does not actuate hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import torch
from torch import nn

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from training.ppo_core import ResidualActorCritic


class ResidualInference(nn.Module):
    def __init__(self,actor):
        super().__init__();self.actor=actor

    def forward(self,observation):
        return .08*torch.tanh(self.actor(observation))


def export(checkpoint_path,output):
    checkpoint_path,output=Path(checkpoint_path),Path(output)
    if output.exists():raise FileExistsError(output)
    checkpoint=torch.load(checkpoint_path,map_location='cpu',weights_only=False)
    model=ResidualActorCritic().eval();model.load_state_dict(checkpoint['model'])
    inference=ResidualInference(model.actor).eval()
    scripted=torch.jit.script(inference)
    output.parent.mkdir(parents=True,exist_ok=True);scripted.save(str(output))
    loaded=torch.jit.load(str(output),map_location='cpu').eval()
    generator=torch.Generator().manual_seed(812)
    probes=torch.randn(32,89,generator=generator)
    with torch.no_grad():
        expected=inference(probes);actual=loaded(probes)
        torch.testing.assert_close(actual,expected,atol=1e-6,rtol=1e-6)
        assert actual.shape==(32,20) and float(actual.abs().max())<=.08
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report={'status':'exported_cpu_equivalence_tested','hardware_verified':False,
            'source_checkpoint_sha256':sha(checkpoint_path),'export_sha256':sha(output),
            'base_actor_sha256':checkpoint['report']['base_actor_sha256'],
            'observation_dim':89,'action_dim':20,'residual_bound_rad':.08,
            'policy_joint_names':checkpoint['policy_joint_names'],
            'observation_contract':'69 K1 observations BEFORE frozen actor step, plus20 previous physical residual radians',
            'application':'Add to20 frozen actor filtered joint targets by name; keep head targets unchanged',
            'max_export_error':float((actual-expected).abs().max()),
            'limits':['synthetic input equivalence only','requires full K1 telemetry/preprocessing adapter','not hardware-ready approval']}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();print(json.dumps(export(args.checkpoint,args.output),indent=2))
