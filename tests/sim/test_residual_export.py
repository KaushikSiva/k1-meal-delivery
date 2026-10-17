import torch
from training.ppo_core import ResidualActorCritic
from deployment.export_residual import export


def test_nonzero_residual_export_matches_and_has_bound(tmp_path):
    model=ResidualActorCritic()
    with torch.no_grad():
        model.actor[-1].weight.normal_(0,.2);model.actor[-1].bias.fill_(.1)
    source=tmp_path/'trained.pt'
    torch.save({'model':model.state_dict(),'report':{'base_actor_sha256':'test-only'},
                'policy_joint_names':[f'joint{i}' for i in range(20)]},source)
    result=export(source,tmp_path/'residual.pt')
    assert result['max_export_error']<1e-6 and not result['hardware_verified']
    output=torch.jit.load(str(tmp_path/'residual.pt'))(torch.full((1,89),1000.))
    assert output.abs().max()<=.08 and torch.isfinite(output).all()
