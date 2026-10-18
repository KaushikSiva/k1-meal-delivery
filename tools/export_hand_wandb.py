"""Import audited hand-contact PPO metrics and matched evaluation into private W&B."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    import wandb
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence',type=Path,required=True)
    ap.add_argument('--receipt',type=Path,required=True)
    args=ap.parse_args();root=args.evidence
    manifest=json.loads((root/'manifest.json').read_text())
    comparison=json.loads((root/'comparison.json').read_text())
    assert manifest['status']=='trained' and comparison['finished_at_utc']
    rows=[json.loads(s) for s in (root/'metrics.jsonl').read_text().splitlines()]
    assert len(rows)==manifest['iterations_completed']
    entity='kaushik-siva88';project='k1-meal-delivery-20261017'
    api=wandb.Api()
    from wandb_gql import gql
    privacy=api.client.execute(gql('query($p:String!,$e:String!){project(name:$p,entityName:$e){access}}'),
                               variable_values={'p':project,'e':entity})
    assert privacy['project']['access'].upper()=='PRIVATE'
    run=wandb.init(entity=entity,project=project,id='hand-ppo-01-historical',resume='never',
        name='Hand-contact PPO 01 (historical import)',job_type='historical-metrics-import',
        config=dict(manifest,historical_import=True,training_performed_by_export=False),
        tags=['simulation','hand-contact','ppo','historical-import'],
        settings=wandb.Settings(disable_git=True,disable_code=True,console='off',silent=True,save_code=False))
    for row in rows:
        values={k:v for k,v in row.items() if isinstance(v,(int,float))}
        values.update(dict(zip(['loss/policy','loss/value','entropy'],row['loss_means'])))
        run.log(values,step=row['iteration'])
    for mode in ['baseline','trained_residual']:
        trials=[t for t in comparison['trials'] if t['mode']==mode]
        run.summary[mode+'_passes']=sum(t['diagnostic_pass'] for t in trials)
        run.summary[mode+'_attempts']=len(trials)
    run.summary['delivery_improvement_established']=False
    artifact=wandb.Artifact('hand-ppo-01-evidence',type='training-evidence')
    names=['manifest.json','metrics.jsonl','comparison.json','protocol.json']
    for name in names:artifact.add_file(str(root/name),name=name)
    run.log_artifact(artifact)
    receipt=dict(url=run.url,id=run.id,metric_rows=len(rows),historical_import=True,
                 file_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names})
    run.finish()
    saved=api.run(f'{entity}/{project}/{receipt["id"]}')
    assert saved.state=='finished'
    receipt['verified_remote_state']=saved.state
    args.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
