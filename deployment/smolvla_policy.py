"""Recorded-checkpoint inference for the bounded subgoal interface; no actuator API."""
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from vla.adapter import VLAProposal


class SmolVLAProposalPolicy:
    def __init__(self, checkpoint: Path, seed=9101):
        import torch
        from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
        self.torch=torch
        self.checkpoint=Path(checkpoint)
        self.manifest=json.loads((self.checkpoint/'manifest.json').read_text())
        h=hashlib.sha256()
        with (self.checkpoint/'policy/model.safetensors').open('rb') as f:
            while data:=f.read(8*1024*1024):h.update(data)
        self.sha256=h.hexdigest()
        if self.sha256!=self.manifest['checkpoint_files']['policy/model.safetensors']:
            raise ValueError('Checkpoint hash mismatch')
        self.policy=SmolVLAPolicy.from_pretrained(self.checkpoint/'policy',strict=True)
        self.policy.eval()
        norm=json.loads((self.checkpoint/'normalization.json').read_text())
        self.mean=np.asarray(norm['mean'],np.float32);self.std=np.asarray(norm['std'],np.float32)
        if self.mean.shape!=(16,) or self.std.shape!=(16,) or not np.all(self.std>0):
            raise ValueError('Invalid checkpoint normalization')
        self.tokenizer=self.policy.model.vlm_with_expert.processor.tokenizer
        torch.manual_seed(seed)

    def propose(self, inputs):
        torch=self.torch
        started=time.monotonic()
        image=np.asarray(inputs['observation.images.head'])
        state=np.asarray(inputs['observation.state'],np.float32)
        if image.dtype!=np.uint8 or image.shape!=(480,640,3) or state.shape!=(16,) or not np.isfinite(state).all():
            raise ValueError('Invalid recorded-interface observation')
        tok=self.tokenizer([inputs['task']],padding='max_length',
            max_length=self.policy.config.tokenizer_max_length,truncation=True,return_tensors='pt')
        batch={'observation.images.head':torch.from_numpy(image.copy()).permute(2,0,1).unsqueeze(0).to('cuda',dtype=torch.float32)/255,
            'observation.state':torch.from_numpy((state-self.mean)/self.std).unsqueeze(0).to('cuda'),
            'observation.language.tokens':tok['input_ids'].to('cuda'),
            'observation.language.attention_mask':tok['attention_mask'].bool().to('cuda')}
        with torch.inference_mode():actions=self.policy.predict_action_chunk(batch)
        torch.cuda.synchronize()
        a=actions[0].float().cpu().numpy()
        if a.shape!=(10,5) or not np.isfinite(a).all():raise ValueError('Invalid policy output')
        return VLAProposal(a,float(inputs['timestamp']),'smolvla-'+self.sha256[:12],time.monotonic()-started)
