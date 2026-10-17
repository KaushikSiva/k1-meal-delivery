#!/usr/bin/env python3
"""Verify saved GR00T shards and perform one real recorded-observation inference."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np,torch

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--runtime',type=Path,required=True);a=ap.parse_args();r=a.runtime;out=r/'evidence/groot-pilot-02';m=json.loads((out/'manifest.json').read_text());verified={}
 for name,h in m['checkpoint_files'].items():
  if name.startswith('checkpoint/model-') and name.endswith('.safetensors'):
   assert sha(out/name)==h;verified[name]=h
 assert len(verified)==3
 from gr00t.policy.gr00t_policy import Gr00tPolicy
 policy=Gr00tPolicy('NEW_EMBODIMENT',str(out/'checkpoint'),device='cuda:0',strict=True)
 data=r/'smolvla-train-01-input/sensor-dataset-01/validation-00.npz'
 with np.load(data,allow_pickle=False) as z:
  obs={'video':{'head':z['rgb'][0][None,None]},'state':{'telemetry':z['state'][0][None,None]},'language':{'annotation.human.task_description':[[str(z['task'][0])]]}}
 torch.manual_seed(9401);start=time.monotonic();action,info=policy.get_action(obs);torch.cuda.synchronize();elapsed=time.monotonic()-start
 arr=np.asarray(action['subgoal']);assert arr.ndim==3 and arr.shape[0]==1 and arr.shape[-1]==5 and np.isfinite(arr).all()
 result={'checkpoint_shards_verified':verified,'input_npz_sha256':sha(data),'output_shape':list(arr.shape),'output_finite':True,'first_action':arr[0,0].tolist(),'first_inference_seconds':elapsed,'optimizer_updates':0,'actuator_commands':0,'scope':'recorded validation frame checkpoint reload; no delivery performance claim'}
 (out/'reload_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
