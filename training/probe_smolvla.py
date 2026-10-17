#!/usr/bin/env python3
"""GPU feasibility only: custom-shaped inference and backward, no optimizer step.

Synthetic image/state/action tensors test plumbing and memory. They are NOT K1
demonstrations, task evaluation or fine-tuning evidence. No weights are saved.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runtime',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    report={'status':'started','started_at_utc':datetime.now(timezone.utc).isoformat(),
            'evidence_kind':'synthetic_tensor_gpu_feasibility_only','training_performed':False,
            'optimizer_updates':0,'robot_actuated':False,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        import torch
        from lerobot.configs.types import PolicyFeature,FeatureType
        from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
        from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
        torch.manual_seed(8301);torch.set_num_threads(4)
        model_path=args.runtime/'models/smolvla_base'
        cfg=SmolVLAConfig.from_pretrained(model_path)
        cfg.device='cuda';cfg.push_to_hub=False
        cfg.vlm_model_name=str(args.runtime/'models/smolvlm2')
        cfg.load_vlm_weights=False  # full pretrained policy contains the backbone weights
        cfg.input_features={'observation.state':PolicyFeature(FeatureType.STATE,(16,)),
            'observation.images.head':PolicyFeature(FeatureType.VISUAL,(3,480,640))}
        cfg.output_features={'action':PolicyFeature(FeatureType.ACTION,(5,))}
        cfg.chunk_size=10;cfg.n_action_steps=1
        started=time.monotonic()
        policy=SmolVLAPolicy.from_pretrained(model_path,config=cfg,strict=True)
        torch.cuda.synchronize()
        report.update(load_seconds=time.monotonic()-started,
            gpu=torch.cuda.get_device_name(0),torch=torch.__version__,cuda=torch.version.cuda,
            parameter_count=sum(p.numel() for p in policy.parameters()),
            trainable_parameters=sum(p.numel() for p in policy.parameters() if p.requires_grad),
            config={'state_dim':16,'action_dim':5,'camera_count':1,'chunk_size':10,'denoising_steps':cfg.num_steps},
            strict_pretrained_load=True)
        tokenizer=policy.model.vlm_with_expert.processor.tokenizer
        tokens=tokenizer(['deliver the pizza and drink to the table'],padding='max_length',
                         max_length=cfg.tokenizer_max_length,truncation=True,return_tensors='pt')
        batch={'observation.state':torch.zeros((1,16),device='cuda'),
               'observation.images.head':torch.zeros((1,3,480,640),device='cuda'),
               'observation.language.tokens':tokens['input_ids'].to('cuda'),
               'observation.language.attention_mask':tokens['attention_mask'].bool().to('cuda')}
        timings=[]
        for i in range(4):
            torch.cuda.synchronize();t=time.monotonic()
            with torch.inference_mode():action=policy.predict_action_chunk(batch)
            torch.cuda.synchronize();timings.append(time.monotonic()-t)
            assert tuple(action.shape)==(1,10,5) and torch.isfinite(action).all()
        report.update(inference_seconds=timings,output_shape=list(action.shape),
                      output_finite=True,inference_peak_allocated_bytes=torch.cuda.max_memory_allocated())
        policy.train();policy.zero_grad(set_to_none=True);torch.cuda.reset_peak_memory_stats()
        batch['action']=torch.zeros((1,10,5),device='cuda')
        t=time.monotonic();loss,metrics=policy.forward(batch)
        assert torch.isfinite(loss)
        loss.backward();torch.cuda.synchronize()
        gradients=[p.grad for p in policy.parameters() if p.requires_grad and p.grad is not None]
        assert gradients and all(torch.isfinite(g).all() for g in gradients)
        grad_norm=float(torch.sqrt(sum(g.float().square().sum() for g in gradients)))
        assert grad_norm>0
        report.update(status='passed_plumbing_probe',synthetic_loss=float(loss.detach()),
            gradient_norm=grad_norm,backward_seconds=time.monotonic()-t,
            backward_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            limits=['synthetic tensors only','no optimizer step','no trained K1 VLA','no task-performance claim'])
    except Exception as exc:
        import traceback
        report.update(status='failed',error=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))


if __name__=='__main__':main()
