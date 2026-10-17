#!/usr/bin/env python3
"""Explicit historical import of real PPO/SmolVLA metrics; no training runs here.

Uses W&B 0.27.2 SDK. Uploads an allowlist of evidence files, never weights/env.
"""
import argparse,hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--runtime',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    import wandb
    from wandb.apis._generated import CREATE_PROJECT_GQL,UpsertModelInput
    assert wandb.__version__=='0.27.2'
    assert os.environ.get('WANDB_API_KEY'), 'Configure credential outside this script'
    api=wandb.Api();entity=api.default_entity;assert entity
    project='k1-meal-delivery-20261017'
    data=api._service_api.execute_graphql(CREATE_PROJECT_GQL,{'input':UpsertModelInput(name=project,entity_name=entity,access='PRIVATE',description='Real simulator training evidence; retrospective imports explicitly labeled.').model_dump()})
    made=data['result'].get('project') or data['result']['model']
    assert made['access'].upper()=='PRIVATE','Expected private project'
    receipt={'exported_at_utc':datetime.now(timezone.utc).isoformat(),'project_url':f'https://wandb.ai/{entity}/{project}','project_access':made['access'],'historical_import':True,'training_performed_by_export':False,'runs':[]}
    args.output.mkdir(parents=True,exist_ok=False)
    for kind,directory in [('ppo','k1-ppo-02'),('smolvla','smolvla-train-02')]:
        root=args.runtime/'evidence'/directory;manifest=root/'manifest.json';m=json.loads(manifest.read_text());metrics=root/('metrics.jsonl' if kind=='ppo' else 'metrics.json')
        rows=[json.loads(s) for s in metrics.read_text().splitlines()] if kind=='ppo' else json.loads(metrics.read_text())
        keys=['source_hashes','source_sha256','dataset_sha256','seed','num_envs','horizon','iterations_completed','environment_steps','optimizer_steps','residual_bound_rad','base_actor_sha256','final_checkpoint_sha256','optimizer_updates','budget','optimizer','checkpoint_files','data_frames','trainable_parameters','frozen_weights_unchanged','scope','limits','started_at_utc','finished_at_utc']
        config={k:m[k] for k in keys if k in m};config.update(historical_import=True,original_manifest_sha256=sha(manifest),metrics_sha256=sha(metrics),hardware_verified=False,exporter_sha256=sha(Path(__file__)))
        run=wandb.init(entity=entity,project=project,id=directory+'-historical',resume='never',name=directory+' (historical import)',job_type='historical-metrics-import',config=config,tags=['simulation','historical-import',kind],settings=wandb.Settings(disable_git=True,disable_code=True,console='off',silent=True,save_code=False),dir=str(args.output))
        for row in rows:
            values={k:v for k,v in row.items() if isinstance(v,(int,float))}
            if kind=='ppo':values.update({f'reward/{k}':v for k,v in zip(row['component_names'],row['reward_component_means'])})
            run.log(values,step=int(row['iteration'] if kind=='ppo' else row['step']))
        for k in ['initial_evaluation','final_evaluation','environment_steps','optimizer_steps','optimizer_updates','episodes_completed','falls','payload_drops','timeouts','parameter_change_l2','trainable_delta_l2','changed_parameter_tensors','frozen_weights_unchanged','final_checkpoint_sha256','checkpoint_files']:
            if k in m:run.summary[k]=m[k]
        a=wandb.Artifact(directory+'-evidence',type='training-evidence',metadata={'historical_import':True,'weights_uploaded':False})
        a.add_file(str(manifest),name='manifest.json');a.add_file(str(metrics),name=metrics.name);run.log_artifact(a)
        receipt['runs'].append({'kind':kind,'url':run.url,'id':run.id,'metric_rows':len(rows),'manifest_sha256':sha(manifest),'metrics_sha256':sha(metrics)})
        run.finish()
        (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    for row in receipt['runs']:
        saved=api.run(f'{entity}/{project}/{row["id"]}')
        assert saved.state=='finished',saved.state
        row['verified_remote_state']=saved.state
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
