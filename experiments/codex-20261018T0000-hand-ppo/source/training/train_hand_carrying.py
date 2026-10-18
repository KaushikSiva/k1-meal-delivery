"""Train a fresh bounded leg residual using real free hand-contact rollouts."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np
import torch
from training.hand_carry_env import HandCarryEnv
from training.ppo_core import ResidualActorCritic,advantages,update
from deployment.hand_residual import OBSERVATION_DIM,ACTION_DIM,RESIDUAL_BOUND_RAD


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parameter_hash(model):
    h=hashlib.sha256()
    for name,value in model.state_dict().items():
        h.update(name.encode());h.update(value.detach().numpy().tobytes())
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--iterations',type=int,default=128)
    ap.add_argument('--horizon',type=int,default=256)
    ap.add_argument('--seed',type=int,default=9801)
    args=ap.parse_args();assert args.iterations>0 and args.horizon>=8
    args.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);torch.manual_seed(args.seed)
    env=HandCarryEnv(args.output/'environment',args.seed)
    obs=torch.from_numpy(env.reset()).unsqueeze(0)
    model=ResidualActorCritic(OBSERVATION_DIM,ACTION_DIM)
    optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
    source_files=['training/train_hand_carrying.py','training/hand_carry_env.py','training/ppo_core.py',
                  'deployment/hand_residual.py','sim/k1_hand_controller.py','sim/k1_hand_carry.py']
    for name in source_files:
        dst=args.output/'source'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(name,dst)
    report=dict(status='started',started_at_utc=datetime.now(timezone.utc).isoformat(),
                simulator='MuJoCo',training_device='cpu',seed=args.seed,
                training_kind='fresh PPO leg residual with actual free hand-supported payload',
                base_actor_finetuned=False,older_torso_residual_reused=False,
                source_sha256={name:sha(name) for name in source_files},
                base_actor_sha256=sha(env.cfg.policy.checkpoint_path),
                iterations_requested=args.iterations,horizon=args.horizon,
                environment_steps=0,physics_steps=0,optimizer_updates=0,episodes=0,terminated_episodes=0,
                observation_dim=OBSERVATION_DIM,action_dim=ACTION_DIM,residual_bound_rad=RESIDUAL_BOUND_RAD,
                leg_joint_names=[env.cfg.robot.joint_names[i] for i in env.legs],
                all_joint_names=env.cfg.robot.joint_names,
                actor_inputs='gyro, gravity direction from IMU quaternion, commanded velocity,22 joint positions/velocities,12 previous residuals',
                privileged_reward_only='true linear velocity, root height, body tilt, payload shifts/drop',
                scenario='8s episodes:2s stand,4s move,2s stop; randomized initialyaw±.2 and eight fixed command classes',
                command_classes=env.commands.tolist(),learning_rate=3e-4,
                evaluation_used_for_optimization=False,hardware_verified=False,
                initial_parameter_sha256=parameter_hash(model))
    initial={k:v.detach().clone() for k,v in model.state_dict().items()}
    def checkpoint(name):
        p=args.output/name
        torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),
                        report=report,torch_rng_state=torch.get_rng_state()),p)
        return sha(p)
    report['initial_checkpoint_sha256']=checkpoint('initial.pt')
    manifest=args.output/'manifest.json'
    manifest.write_text(json.dumps(report,indent=2)+'\n')
    started=time.monotonic()
    try:
        for iteration in range(args.iterations):
            buffers={k:[] for k in ['obs','action','logprob','value','next_value','reward','terminated','done']}
            for _ in range(args.horizon):
                with torch.no_grad():
                    action,lp,value=model.sample(obs)
                    residual=RESIDUAL_BOUND_RAD*torch.tanh(action[0])
                next_obs,reward,terminated,done,info=env.step(residual.numpy())
                next_obs=torch.from_numpy(next_obs).unsqueeze(0)
                with torch.no_grad():next_value=model.value(next_obs)
                values=dict(obs=obs,action=action,logprob=lp,value=value,next_value=next_value,
                            reward=torch.tensor([reward]),terminated=torch.tensor([terminated]),done=torch.tensor([done]))
                for key,value in values.items():buffers[key].append(value)
                report['environment_steps']+=1;report['physics_steps']+=10
                if done:
                    report['episodes']+=1;report['terminated_episodes']+=int(terminated)
                    obs=torch.from_numpy(env.reset()).unsqueeze(0)
                else:obs=next_obs
            b={k:torch.stack(v) for k,v in buffers.items()}
            advantage,returns=advantages(b['reward'],b['value'],b['next_value'],b['terminated'],b['done'])
            stats=update(model,optimizer,b['obs'],b['action'],b['logprob'],returns,advantage,epochs=4,minibatch=128)
            report['optimizer_updates']+=stats['optimizer_steps']
            report['iterations_completed']=iteration+1
            row=dict(iteration=iteration+1,environment_steps=report['environment_steps'],
                     optimizer_updates=report['optimizer_updates'],reward_mean=float(b['reward'].mean()),
                     episodes=report['episodes'],terminated_episodes=report['terminated_episodes'],
                     elapsed_s=time.monotonic()-started,**stats)
            with (args.output/'metrics.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            manifest.write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(row),flush=True)
        report.update(status='trained',final_parameter_sha256=parameter_hash(model),
                      parameter_change_l2=float(torch.sqrt(sum((v-initial[k]).square().sum() for k,v in model.state_dict().items()))),
                      base_actor_sha256_after=sha(env.cfg.policy.checkpoint_path))
        assert report['base_actor_sha256_after']==report['base_actor_sha256']
        assert report['final_parameter_sha256']!=report['initial_parameter_sha256']
        report['final_checkpoint_sha256']=checkpoint('final.pt')
    except Exception as exc:
        report.update(status='failed',error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        report.update(finished_at_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-started)
        manifest.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
