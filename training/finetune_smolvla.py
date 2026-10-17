#!/usr/bin/env python3
"""Actual bounded-budget imitation updates on recorded sensor-only K1 episodes.

This tiny pilot establishes weight updates, not delivery performance. The base
VLM stays frozen; the existing action expert/projections are fine-tuned.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
import numpy as np


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while data:=f.read(8*1024*1024):h.update(data)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runtime',type=Path,required=True)
    ap.add_argument('--dataset',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    report={'status':'started','started_at_utc':datetime.now(timezone.utc).isoformat(),
            'training_performed':False,'optimizer_updates':0,'hardware_verified':False,
            'scope':'tiny unloaded K1 simulator teacher-imitation pilot',
            'source_sha256':file_sha(__file__),'dataset_sha256':file_sha(args.dataset/'dataset.json')}
    records=[];started=time.monotonic()
    try:
        import torch
        from lerobot.configs.types import PolicyFeature,FeatureType
        from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
        from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
        data=json.loads((args.dataset/'dataset.json').read_text())
        budget=data['protocol']['training_budget'];seed=budget['seed']
        torch.manual_seed(seed);torch.set_num_threads(4);rng=np.random.default_rng(seed)
        model_path=args.runtime/'models/smolvla_base'
        cfg=SmolVLAConfig.from_pretrained(model_path)
        cfg.device='cuda';cfg.push_to_hub=False
        cfg.vlm_model_name=str(args.runtime/'models/smolvlm2');cfg.load_vlm_weights=False
        cfg.input_features={'observation.state':PolicyFeature(FeatureType.STATE,(16,)),
            'observation.images.head':PolicyFeature(FeatureType.VISUAL,(3,480,640))}
        cfg.output_features={'action':PolicyFeature(FeatureType.ACTION,(5,))}
        cfg.chunk_size=budget['chunk_size'];cfg.n_action_steps=1
        policy=SmolVLAPolicy.from_pretrained(model_path,config=cfg,strict=True)
        tokenizer=policy.model.vlm_with_expert.processor.tokenizer
        mean=np.array(data['normalization']['mean'],np.float32)
        std=np.array(data['normalization']['std'],np.float32)
        episodes=[];indices={'train':[],'validation':[]}
        for item in data['episodes']:
            if not item['included']:continue
            path=args.dataset/item['file']
            if file_sha(path)!=item['sha256']:raise ValueError('dataset checksum mismatch')
            with np.load(path,allow_pickle=False) as f:ep={k:f[k] for k in f.files}
            tokens=tokenizer(ep['task'].tolist(),padding='max_length',
                max_length=cfg.tokenizer_max_length,truncation=True,return_tensors='pt')
            ep['tokens']=tokens['input_ids'];ep['mask']=tokens['attention_mask'].bool()
            ep['state']=(ep['state']-mean)/std
            ep_id=len(episodes);episodes.append(ep)
            indices[item['split']].extend((ep_id,j) for j in range(len(ep['action'])))
        if not indices['train']:raise ValueError('no training data')
        def batch(pairs):
            images=[];states=[];actions=[];masks=[];tokens=[];language_masks=[]
            for ep_id,j in pairs:
                ep=episodes[ep_id];steps=np.arange(j,j+cfg.chunk_size)
                images.append(ep['rgb'][j]);states.append(ep['state'][j])
                actions.append(ep['action'][np.minimum(steps,len(ep['action'])-1)])
                masks.append(steps>=len(ep['action']));tokens.append(ep['tokens'][j]);language_masks.append(ep['mask'][j])
            return {'observation.images.head':torch.from_numpy(np.stack(images)).permute(0,3,1,2).to('cuda',dtype=torch.float32)/255.,
                'observation.state':torch.from_numpy(np.stack(states)).to('cuda'),
                'action':torch.from_numpy(np.stack(actions)).to('cuda'),
                'action_is_pad':torch.from_numpy(np.stack(masks)).to('cuda'),
                'observation.language.tokens':torch.stack(tokens).to('cuda'),
                'observation.language.attention_mask':torch.stack(language_masks).to('cuda')}
        def fingerprint(trainable):
            h=hashlib.sha256()
            for name,p in policy.named_parameters():
                if p.requires_grad==trainable:
                    h.update(name.encode());h.update(str(p.dtype).encode());h.update(str(tuple(p.shape)).encode())
                    h.update(p.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
            return h.hexdigest()
        def evaluate():
            result={};policy.eval()
            with torch.inference_mode(),torch.random.fork_rng(devices=[0]):
                for split,pairs in indices.items():
                    if not pairs:result[split]=None;continue
                    chosen=[pairs[i] for i in np.linspace(0,len(pairs)-1,min(16,len(pairs)),dtype=int)]
                    losses=[];action_errors=[]
                    torch.manual_seed(8701)
                    for offset in range(0,len(chosen),4):
                        b=batch(chosen[offset:offset+4]);loss,_=policy.forward(b)
                        actions=policy.predict_action_chunk(b)
                        losses.append((float(loss),len(b['action'])))
                        action_errors.extend((actions[:,0]-b['action'][:,0]).square().mean(dim=-1).cpu().tolist())
                    result[split]={'sampled_rows':len(chosen),
                        'flow_loss':sum(l*n for l,n in losses)/sum(n for _,n in losses),
                        'first_action_normalized_mse':float(np.mean(action_errors))}
            return result
        params=[p for p in policy.parameters() if p.requires_grad]
        report.update(gpu=torch.cuda.get_device_name(0),torch=torch.__version__,
            parameters=sum(p.numel() for p in policy.parameters()),trainable_parameters=sum(p.numel() for p in params),
            data_frames={k:len(v) for k,v in indices.items()},budget=budget,
            initial_trainable_sha256=fingerprint(True),initial_frozen_sha256=fingerprint(False),
            initial_evaluation=evaluate(),
            evaluation_scope='16 evenly spaced rows per split, fixed RNG; offline imitation only')
        initial={n:p.detach().cpu().clone() for n,p in policy.named_parameters() if p.requires_grad}
        optimizer=torch.optim.AdamW(params,lr=budget['learning_rate'],betas=(.9,.95),weight_decay=.01)
        report['optimizer']={'name':'AdamW','betas':[.9,.95],'weight_decay':.01,'max_grad_norm':10.}
        torch.cuda.reset_peak_memory_stats();training_start=time.monotonic()
        for step in range(budget['optimizer_steps']):
            pairs=[indices['train'][i] for i in rng.integers(len(indices['train']),size=budget['batch_size'])]
            policy.train();optimizer.zero_grad(set_to_none=True)
            loss,_=policy.forward(batch(pairs))
            if not torch.isfinite(loss):raise RuntimeError('nonfinite loss')
            loss.backward();norm=torch.nn.utils.clip_grad_norm_(params,10.,error_if_nonfinite=True)
            optimizer.step();report.update(training_performed=True,optimizer_updates=step+1)
            records.append({'step':step+1,'loss':float(loss.detach()),'gradient_norm':float(norm),
                            'elapsed_seconds':time.monotonic()-training_start})
            if (step+1)%20==0:
                (args.output/'progress.json').write_text(json.dumps(records[-1])+'\n')
                print(json.dumps(records[-1]),flush=True)
        report['training_seconds']=time.monotonic()-training_start
        report['peak_allocated_gpu_bytes']=torch.cuda.max_memory_allocated()
        report['final_evaluation']=evaluate()
        report['final_trainable_sha256']=fingerprint(True);report['final_frozen_sha256']=fingerprint(False)
        sq=0.;changed=0
        for n,p in policy.named_parameters():
            if p.requires_grad:
                diff=p.detach().cpu()-initial[n];sq+=float(diff.double().square().sum());changed+=int(torch.any(diff!=0))
        report.update(changed_parameter_tensors=changed,trainable_delta_l2=sq**.5,
            frozen_weights_unchanged=report['initial_frozen_sha256']==report['final_frozen_sha256'])
        if not changed or not report['frozen_weights_unchanged']:raise RuntimeError('weight accounting failed')
        policy.save_pretrained(args.output/'policy')
        (args.output/'normalization.json').write_text(json.dumps(data['normalization'],indent=2)+'\n')
        report['checkpoint_files']={str(p.relative_to(args.output)):file_sha(p)
            for p in (args.output/'policy').rglob('*') if p.is_file()}
        report.update(status='trained',limits=['tiny demonstration dataset','one training seed',
            'unloaded simple MuJoCo room only','no closed-loop VLA evaluation','no hardware validation'])
    except Exception as exc:
        import traceback
        report.update(status='failed',error=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        report.update(finished_at_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-started)
        (args.output/'metrics.json').write_text(json.dumps(records,indent=2)+'\n')
        (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
