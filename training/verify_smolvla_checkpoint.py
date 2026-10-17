#!/usr/bin/env python3
"""Strictly reload the saved pilot and infer on one recorded validation frame."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint',type=Path,required=True)
    ap.add_argument('--dataset',type=Path,required=True)
    args=ap.parse_args()
    import torch
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    torch.set_num_threads(4);torch.manual_seed(8801)
    m=json.loads((args.checkpoint/'manifest.json').read_text())
    policy=SmolVLAPolicy.from_pretrained(args.checkpoint/'policy',strict=True)
    for trainable,key in [(True,'final_trainable_sha256'),(False,'final_frozen_sha256')]:
        h=hashlib.sha256()
        for name,p in policy.named_parameters():
            if p.requires_grad==trainable:
                h.update(name.encode());h.update(str(p.dtype).encode());h.update(str(tuple(p.shape)).encode())
                h.update(p.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
        if h.hexdigest()!=m[key]:raise RuntimeError('Reloaded weights differ from training result')
    data=json.loads((args.dataset/'dataset.json').read_text())
    item=next(e for e in data['episodes'] if e['included'] and e['split']=='validation')
    with np.load(args.dataset/item['file'],allow_pickle=False) as f:
        image=f['rgb'][0];state=f['state'][0];task=str(f['task'][0])
    n=json.loads((args.checkpoint/'normalization.json').read_text())
    state=((state-np.asarray(n['mean'],np.float32))/np.asarray(n['std'],np.float32)).astype(np.float32)
    tok=policy.model.vlm_with_expert.processor.tokenizer([task],padding='max_length',
        max_length=policy.config.tokenizer_max_length,truncation=True,return_tensors='pt')
    batch={'observation.images.head':torch.from_numpy(image).permute(2,0,1).unsqueeze(0).to('cuda',dtype=torch.float32)/255,
        'observation.state':torch.from_numpy(state).unsqueeze(0).to('cuda'),
        'observation.language.tokens':tok['input_ids'].to('cuda'),
        'observation.language.attention_mask':tok['attention_mask'].bool().to('cuda')}
    torch.cuda.synchronize();start=time.monotonic()
    with torch.inference_mode():actions=policy.predict_action_chunk(batch)
    torch.cuda.synchronize()
    assert tuple(actions.shape)==(1,10,5) and torch.isfinite(actions).all()
    report={'status':'strict_reload_and_recorded_input_passed','checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'training_performed':False,'checkpoint_trainable_and_frozen_hashes_match':True,
        'episode':item['id'],'frame':0,'inference_seconds':time.monotonic()-start,
        'output_shape':list(actions.shape),'finite':True,'robot_actuated':False}
    (args.checkpoint/'reload_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
