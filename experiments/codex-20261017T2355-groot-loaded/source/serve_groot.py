"""Localhost-only GR00T proposal server; no robot/actuator API.

Checkpoint hashes and strict model loading are verified before serving. Transport
uses the existing RemoteVLAClient protocol, carried over an SSH tunnel for tests.
"""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import time
import numpy as np
import torch


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(8*1024*1024):h.update(chunk)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint',type=Path,required=True)
    ap.add_argument('--port',type=int,default=8766)
    ap.add_argument('--seed',type=int,default=9701)
    args=ap.parse_args()
    import training.groot_k1_config
    from gr00t.policy.gr00t_policy import Gr00tPolicy
    manifest=json.loads((args.checkpoint/'manifest.json').read_text())
    hashes={}
    for name,expected in manifest['checkpoint_files'].items():
        if name.startswith('checkpoint/model-') and name.endswith('.safetensors'):
            actual=sha(args.checkpoint/name)
            if actual!=expected:raise ValueError('Checkpoint shard mismatch: '+name)
            hashes[name]=actual
    if len(hashes)!=3:raise ValueError('Expected three audited checkpoint shards')
    identity=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    policy=Gr00tPolicy('NEW_EMBODIMENT',str(args.checkpoint/'checkpoint'),device='cuda:0',strict=True)
    torch.manual_seed(args.seed)
    health=dict(model_id='groot-'+identity[:12],checkpoint_shards=hashes,
                optimizer_updates=manifest['optimizer_updates'],seed=args.seed,
                server_source_sha256=sha(Path(__file__)),actuator_api=False)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def reply(self,status,data):
            encoded=json.dumps(data).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(encoded)))
            self.end_headers();self.wfile.write(encoded)

        def do_GET(self):
            self.reply(200,health) if self.path=='/health' else self.reply(404,{'error':'Unknown path'})

        def do_POST(self):
            if self.path!='/propose':return self.reply(404,{'error':'Unknown path'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=2_000_000:raise ValueError('Invalid request size')
                request=json.loads(self.rfile.read(length))
                state=np.asarray(request['state'],np.float32)
                if state.shape!=(16,) or not np.isfinite(state).all():raise ValueError('Invalid state')
                image=request['image']
                if image['shape']!=[480,640,3] or image['dtype']!='uint8':raise ValueError('Invalid image metadata')
                raw=base64.b64decode(image['b64'],validate=True)
                if len(raw)!=480*640*3:raise ValueError('Invalid image bytes')
                rgb=np.frombuffer(raw,np.uint8).reshape(480,640,3).copy()
                task=request['task']
                if not isinstance(task,str) or not 0<len(task)<=4096:raise ValueError('Invalid task')
                obs={'video':{'head':rgb[None,None]},'state':{'telemetry':state[None,None]},
                     'language':{'annotation.human.task_description':[[task]]}}
                started=time.monotonic()
                with torch.inference_mode():actions,_=policy.get_action(obs)
                torch.cuda.synchronize()
                output=np.asarray(actions['subgoal'])
                if output.shape!=(1,10,5) or not np.isfinite(output).all():raise ValueError('Invalid model actions')
                self.reply(200,dict(actions=output[0].tolist(),model_id=health['model_id'],
                                    inference_seconds=time.monotonic()-started))
            except (ValueError,KeyError,TypeError) as exc:
                self.reply(400,{'error':str(exc)})

    print(json.dumps(dict(status='ready',**health)),flush=True)
    HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


if __name__=='__main__':main()
