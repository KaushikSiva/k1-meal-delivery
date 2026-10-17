#!/usr/bin/env python3
"""Small genuine GR00T optimizer pilot via the pinned official training pipeline."""
import argparse,hashlib,json,time
from datetime import datetime,timezone
from pathlib import Path
import torch

def file_sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    return h.hexdigest()
def fingerprints(model):
    groups={True:hashlib.sha256(),False:hashlib.sha256()};counts={True:0,False:0}
    for name,p in model.named_parameters():
        h=groups[p.requires_grad];h.update(name.encode());h.update(p.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes());counts[p.requires_grad]+=p.numel()
    return {'trainable_sha256':groups[True].hexdigest(),'frozen_sha256':groups[False].hexdigest(),'trainable_parameters':counts[True],'frozen_parameters':counts[False]}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--runtime',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--steps',type=int,default=20);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import training.groot_k1_config
    from gr00t.configs.base_config import get_default_config
    from gr00t.data.embodiment_tags import EmbodimentTag
    import gr00t.experiment.experiment as experiment
    report={'status':'started','started_at_utc':datetime.now(timezone.utc).isoformat(),'scope':f'{a.steps}-update custom bounded-subgoal training; no delivery-performance claim','hardware_verified':False,'training_performed':False,'optimizer_updates':0,'source_revision':'dac54b313160c201c450f97df0fd74ebd379c892','source_sha256':file_sha(Path(__file__)),'dataset_manifest_sha256':file_sha(a.runtime/'groot-dataset-01/manifest.json'),'budget':{'optimizer_steps':a.steps,'batch_size':1,'learning_rate':1e-4},'torch':torch.__version__}
    start=time.monotonic();original=experiment.Gr00tTrainer
    class AuditedTrainer(original):
        def train(self,*args,**kwargs):
            report['initial']=fingerprints(self.model);(a.output/'manifest.json').write_text(json.dumps(report,indent=2))
            result=super().train(*args,**kwargs)
            report['final']=fingerprints(self.model);report['optimizer_updates']=int(self.state.global_step);report['training_performed']=self.state.global_step>0
            report['frozen_parameters_unchanged']=report['initial']['frozen_sha256']==report['final']['frozen_sha256']
            report['trainable_parameters_changed']=report['initial']['trainable_sha256']!=report['final']['trainable_sha256']
            (a.output/'metrics.json').write_text(json.dumps(self.state.log_history,indent=2)+'\n')
            assert report['optimizer_updates']==a.steps and report['frozen_parameters_unchanged'] and report['trainable_parameters_changed']
            return result
    experiment.Gr00tTrainer=AuditedTrainer
    config=get_default_config().load_dict({'data':{'download_cache':False,'datasets':[{'dataset_paths':[str(a.runtime/'groot-dataset-01/train')],'mix_ratio':1.,'embodiment_tag':EmbodimentTag.NEW_EMBODIMENT.value}]}})
    config.load_config_path=None
    config.model.model_name=str(a.runtime/'models/cosmos_reason2');config.model.tune_llm=False;config.model.tune_visual=False;config.model.tune_projector=True;config.model.tune_diffusion_model=True
    config.model.load_bf16=False;config.model.reproject_vision=False;config.model.backbone_trainable_params_fp32=True;config.model.use_relative_action=True
    config.training.start_from_checkpoint=str(a.runtime/'models/groot_n1_7');config.training.output_dir=str(a.output/'checkpoint');config.training.experiment_name=None
    config.training.global_batch_size=1;config.training.num_gpus=1;config.training.max_steps=a.steps;config.training.learning_rate=1e-4;config.training.optim='adamw_torch';config.training.dataloader_num_workers=2;config.training.logging_steps=1
    config.training.save_steps=a.steps+1;config.training.save_total_limit=1;config.training.save_only_model=True;config.training.use_wandb=True;config.training.wandb_project='k1-meal-delivery-20261017';config.training.upload_checkpoints=False
    config.data.seed=9301;config.data.shard_size=256;config.data.num_shards_per_epoch=4;config.data.episode_sampling_rate=1.
    try:
        experiment.run(config)
        report['checkpoint_files']={str(p.relative_to(a.output)):file_sha(p) for p in (a.output/'checkpoint').rglob('*') if p.is_file() and p.suffix in ['.json','.safetensors']}
        report['status']='trained'
    except Exception as exc:
        report.update(status='failed',error=f'{type(exc).__name__}: {exc}');raise
    finally:
        report.update(finished_at_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,peak_allocated_gpu_bytes=torch.cuda.max_memory_allocated())
        (a.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
        import wandb
        if wandb.run:
            wandb.run.summary.update({k:v for k,v in report.items() if k in ['optimizer_updates','frozen_parameters_unchanged','trainable_parameters_changed','checkpoint_files','status','dataset_manifest_sha256','source_sha256']});wandb.finish(exit_code=0 if report['status']=='trained' else 1)
        print(json.dumps(report,indent=2))
if __name__=='__main__':main()
