#!/usr/bin/env python3
"""Convert existing qualified NPZ episodes to GR00T LeRobot v2, preserving splits."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import imageio.v2 as imageio

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):p.write_text(json.dumps(data,indent=2)+'\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dataset',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    source=json.loads((a.dataset/'dataset.json').read_text());report={'source_dataset_sha256':sha(a.dataset/'dataset.json'),'converter_sha256':sha(Path(__file__)),'training_performed':False,'splits':{}}
    for split in ['train','validation']:
        root=a.output/split;meta=root/'meta';meta.mkdir(parents=True)
        data=root/'data/chunk-000';data.mkdir(parents=True);video=root/'videos/chunk-000/observation.images.head';video.mkdir(parents=True)
        episodes=[];tasks={};total=0;source_episodes=[]
        for ep in source['episodes']:
            if not ep['included'] or ep['split']!=split:continue
            path=a.dataset/ep['file'];assert sha(path)==ep['sha256']
            with np.load(path,allow_pickle=False) as z:
                state=z['state'];action=z['action'];rgb=z['rgb'];text=z['task'];time=z['timestamp']
                n=len(state);assert state.shape==(n,16) and action.shape==(n,5) and rgb.shape==(n,480,640,3)
                assert np.isfinite(state).all() and np.isfinite(action).all() and rgb.dtype==np.uint8
                assert np.allclose(np.diff(time),.2,atol=1e-6)
                ei=len(episodes);indices=[]
                for t in text:
                    t=str(t)
                    if t not in tasks:tasks[t]=len(tasks)
                    indices.append(tasks[t])
                rows={'observation.state':list(state),'action':list(action),'timestamp':np.arange(n,dtype=np.float32)/5,'frame_index':np.arange(n,dtype=np.int64),'episode_index':np.full(n,ei,dtype=np.int64),'index':np.arange(total,total+n,dtype=np.int64),'task_index':indices,'annotation.human.task_description':indices,'next.reward':np.zeros(n,dtype=np.float32),'next.done':[False]*(n-1)+[True]}
                parquet=data/f'episode_{ei:06d}.parquet';pd.DataFrame(rows).to_parquet(parquet,index=False)
                back=pd.read_parquet(parquet);assert np.array_equal(np.stack(back['observation.state']),state);assert np.array_equal(np.stack(back['action']),action)
                with imageio.get_writer(video/f'episode_{ei:06d}.mp4',fps=5,codec='libx264rgb',pixelformat='rgb24',macro_block_size=1,ffmpeg_params=['-crf','0','-preset','fast']) as writer:
                    for frame in rgb:writer.append_data(frame)
                # Independently decode every lossless frame and check byte equality.
                with imageio.get_reader(video/f'episode_{ei:06d}.mp4') as reader:
                    count=0
                    for count,frame in enumerate(reader,1):assert np.array_equal(frame,rgb[count-1])
                    assert count==n
                episodes.append({'episode_index':ei,'tasks':list(dict.fromkeys(map(str,text))),'length':n});source_episodes.append({'original_id':ep['id'],'npz_sha256':ep['sha256'],'frames':n});total+=n
        (meta/'episodes.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in episodes));(meta/'tasks.jsonl').write_text(''.join(json.dumps({'task_index':i,'task':t})+'\n' for t,i in tasks.items()))
        write(meta/'modality.json',{'state':{'telemetry':{'start':0,'end':16}},'action':{'subgoal':{'start':0,'end':5}},'video':{'head':{'original_key':'observation.images.head'}},'annotation':{'human.task_description':{'original_key':'annotation.human.task_description'}}})
        features={k:{'dtype':dtype,'shape':[dim],'names':None} for k,dtype,dim in [('observation.state','float32',16),('action','float32',5),('timestamp','float32',1),('frame_index','int64',1),('episode_index','int64',1),('index','int64',1),('task_index','int64',1),('annotation.human.task_description','int64',1)]}
        features['observation.images.head']={'dtype':'video','shape':[480,640,3],'names':['height','width','channels'],'info':{'video.height':480,'video.width':640,'video.codec':'h264','video.pix_fmt':'gbrp','video.is_depth_map':False,'video.fps':5,'video.channels':3,'has_audio':False}}
        write(meta/'info.json',{'codebase_version':'v2.1','robot_type':'k1_bounded_subgoal_simulator','total_episodes':len(episodes),'total_frames':total,'total_tasks':len(tasks),'total_chunks':1,'total_videos':len(episodes),'chunks_size':1000,'fps':5,'splits':{split:f'0:{len(episodes)}'},'data_path':'data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet','video_path':'videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4','features':features})
        report['splits'][split]={'episodes':source_episodes,'frames':total,'state_action_parquet_exact':True,'decoded_video_rgb_exact':True,'files':{str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}}
    write(a.output/'manifest.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
