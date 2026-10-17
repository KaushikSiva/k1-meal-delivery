#!/usr/bin/env python3
"""Real Isaac/PhysX rollouts and PPO updates for a bounded carrying residual.

The official locomotion actor stays frozen. This trains a NEW residual, not VLA
or direct base-actor fine-tuning. Empty development floor, fixed supported tray,
free box/drink. World/payload truth enters rewards and terminations only.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--num-envs',type=int,default=32)
p.add_argument('--iterations',type=int,default=100)
p.add_argument('--horizon',type=int,default=64)
p.add_argument('--seed',type=int,default=7101)
args=p.parse_args();assert 1<=args.num_envs<=128 and args.iterations>0
args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=False)
manifest=args.output/'manifest.json'
hashfile=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sources=['training/train_carrying.py','training/ppo_core.py','sim/k1_batch_policy.py',
         'sim/k1_payload.py','sim/k1_payload.json','sim/k1_isaac_nominal.json']
basepath=ROOT/'sim/vendor/booster_deploy/tasks/locomotion/robots/k1/models/k1_walk.pt'
report=dict(status='started',started_at_utc=datetime.now(timezone.utc).isoformat(),
    training_kind='new bounded residual PPO around frozen official actor',
    base_actor_finetuned=False,vla_trained=False,base_actor_sha256=hashfile(basepath),
    source_hashes={s:hashfile(ROOT/s) for s in sources},seed=args.seed,
    num_envs=args.num_envs,iterations_requested=args.iterations,horizon=args.horizon,
    environment_steps=0,physics_steps=0,optimizer_steps=0,iterations_completed=0,
    residual_bound_rad=.08,actor_observations='69 deployable K1 signals +20 previous residuals',
    privileged_inputs='reward/termination: true velocity, root height, payload pose; excluded from actor and critic',
    scenario='development flat floor; 8s episodes,2s stand/4s move/2s stop; speed0.30–0.40m/s',
    limits=['fixed provisional payload/attachment','no navigation or vision training',
            'not a held-out evaluation','no hardware validation'])
def save_manifest():manifest.write_text(json.dumps(report,indent=2)+'\n')
save_manifest();app=None
try:
    from isaaclab.app import AppLauncher
    app=AppLauncher(headless=True,enable_cameras=False).app
    import torch
    import xml.etree.ElementTree as ET
    from pxr import UsdGeom,Gf
    import isaaclab.sim as sim_utils
    from isaaclab.assets import Articulation,ArticulationCfg
    from isaaclab.actuators import IdealPDActuatorCfg
    from isaaclab.utils.math import quat_apply_inverse
    from sim.k1_payload import load_config,make_supported_urdf,spawn_payload
    from sim.k1_batch_policy import BatchedK1Policy
    from training.ppo_core import ResidualActorCritic,advantages,update
    torch.manual_seed(args.seed);torch.cuda.manual_seed_all(args.seed)
    device='cuda:0';n=args.num_envs;dt=.002;policy_dt=.02
    sim=sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=dt,device=device))
    # Locally generated collider avoids downloading an unrelated ground asset.
    ground=sim_utils.CuboidCfg(size=(200.,200.,.1),collision_props=sim_utils.CollisionPropertiesCfg(),
        physics_material=sim_utils.RigidBodyMaterialCfg(static_friction=.7,dynamic_friction=.6,restitution=0.))
    ground.func('/World/Ground',ground,translation=(0.,0.,-.05))
    origins=torch.tensor([((i%8)*8.,(i//8)*8.,0.) for i in range(n)],device=device)
    for i in range(n):
        xf=UsdGeom.Xform.Define(sim.stage,f'/World/envs/env_{i}')
        xf.AddTranslateOp().Set(Gf.Vec3d(*origins[i].cpu().tolist()))
    payload_config=load_config();report['payload_config']=payload_config
    urdf=make_supported_urdf(ROOT/'sim/vendor/booster_assets/robots/K1/K1_22dof.urdf',args.output/'loaded.urdf',payload_config)
    joints=json.loads((ROOT/'sim/k1_isaac_nominal.json').read_text())['joints']
    armature={j.attrib['name']:float(j.attrib['armature']) for j in ET.parse(ROOT/'sim/vendor/booster_assets/robots/K1/K1_22dof.xml').iter('joint') if 'armature' in j.attrib}
    cfg=ArticulationCfg(prim_path='/World/envs/env_.*/K1',
        spawn=sim_utils.UrdfFileCfg(asset_path=str(urdf),usd_dir=str(args.output/'converted'),
            fix_base=False,merge_fixed_joints=True,force_usd_conversion=True,replace_cylinders_with_capsules=False,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=False,max_depenetration_velocity=1),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(enabled_self_collisions=True,
                solver_position_iteration_count=8,solver_velocity_iteration_count=4),
            joint_drive=sim_utils.UrdfConverterCfg.JointDriveCfg(
                gains=sim_utils.UrdfConverterCfg.JointDriveCfg.PDGainsCfg(stiffness=0,damping=0))),
        init_state=ArticulationCfg.InitialStateCfg(pos=(0.,0.,.6),
            joint_pos={name:float(v['position']) for name,v in joints.items()},joint_vel={'.*':0.0}),
        actuators={'all':IdealPDActuatorCfg(joint_names_expr=['.*'],armature=armature,
            effort_limit={name:float(v['effort_limit']) for name,v in joints.items()},
            effort_limit_sim={name:float(v['effort_limit']) for name,v in joints.items()},
            stiffness={name:float(v['stiffness']) for name,v in joints.items()},
            damping={name:float(v['damping']) for name,v in joints.items()})})
    robot=Articulation(cfg)
    payload=spawn_payload((0.,0.,.6),payload_config,prim_prefix='/World/envs/env_.*')
    sim.reset()
    assert robot.data.joint_pos.shape==(n,22)
    masses=robot.root_physx_view.get_masses().sum(-1)
    expected=sum(float(m.attrib['value']) for m in ET.parse(urdf).findall('link/inertial/mass'))
    assert torch.allclose(masses,torch.full_like(masses,expected),atol=1e-4)
    for name,obj in payload.items():
        assert obj.data.root_pos_w.shape==(n,3)
        assert torch.allclose(obj.root_physx_view.get_masses(),torch.full_like(obj.root_physx_view.get_masses(),payload_config[name]['mass_kg']),atol=1e-5)
    # Resolve each view's actual order. PhysX may order env_10 before env_2.
    robot_origins=torch.tensor([origins[int(path.split('/env_')[1].split('/')[0])].cpu().tolist()
                                for path in robot.root_physx_view.prim_paths],device=device)
    payload_origins={name:torch.tensor([origins[int(path.split('/env_')[1].split('/')[0])].cpu().tolist()
                        for path in obj.root_physx_view.prim_paths],device=device) for name,obj in payload.items()}
    for name in payload:assert torch.equal(robot_origins,payload_origins[name]),'Robot/payload view order differs'
    report.update(verified_robot_mass_kg=float(masses[0]),verified_instances=n,
                  robot_view_paths=list(robot.root_physx_view.prim_paths))
    base=BatchedK1Policy(robot.joint_names,n,device)
    model=ResidualActorCritic().to(device);optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
    initial_parameters={name:value.detach().clone() for name,value in model.named_parameters()}
    def parameter_hash():
        h=hashlib.sha256()
        for name,value in model.state_dict().items():
            h.update(name.encode());h.update(value.detach().cpu().numpy().tobytes())
        return h.hexdigest()
    report['initial_parameter_sha256']=parameter_hash()
    def checkpoint(name):
        path=args.output/name
        torch.save({'model':model.state_dict(),'optimizer':optimizer.state_dict(),
            'report':report,'joint_names':robot.joint_names,'policy_joint_names':base.cfg.policy.policy_joint_names,
            'torch_rng_state':torch.get_rng_state(),'cuda_rng_state':torch.cuda.get_rng_state()},path)
        return hashfile(path)
    report['initial_checkpoint_sha256']=checkpoint('initial.pt')
    previous=torch.zeros(n,20,device=device);episode_steps=torch.zeros(n,dtype=torch.long,device=device)
    speeds=torch.zeros(n,device=device);commands=torch.zeros(n,3,device=device)
    completed=falls=drops=timeouts=0
    def reset(ids):
        states=robot.data.default_root_state[ids].clone();states[:,:3]+=robot_origins[ids]
        robot.write_root_pose_to_sim(states[:,:7],env_ids=ids)
        robot.write_root_velocity_to_sim(states[:,7:],env_ids=ids)
        robot.write_joint_state_to_sim(robot.data.default_joint_pos[ids],robot.data.default_joint_vel[ids],env_ids=ids)
        robot.reset(ids)
        for obj in payload.values():
            states=obj.data.default_root_state[ids].clone();states[:,:3]+=robot_origins[ids]
            obj.write_root_pose_to_sim(states[:,:7],env_ids=ids)
            obj.write_root_velocity_to_sim(states[:,7:],env_ids=ids);obj.reset(ids)
        base.reset(ids);previous[ids]=0;episode_steps[ids]=0
        speeds[ids]=.30+.10*torch.rand(len(ids),device=device)
    def observations():
        moving=(episode_steps>=100)&(episode_steps<300)
        commands.zero_();commands[:,0]=speeds*moving
        return torch.cat((base.observe(robot.data,commands),previous),-1)
    reset(torch.arange(n,device=device));obs=observations()
    save_manifest();start=time.monotonic()
    metrics=args.output/'metrics.jsonl'
    for iteration in range(args.iterations):
        buffers={k:[] for k in ['obs','action','logprob','value','next_value','reward','terminated','done']}
        reward_terms=[]
        for _ in range(args.horizon):
            with torch.no_grad():
                action,logprob,value=model.sample(obs)
                residual=.08*torch.tanh(action)
                target=base.step(robot.data,commands)
                target[:,base.policy_indices]+=residual
                for substep in range(10):
                    robot.set_joint_position_target(target);robot.write_data_to_sim()
                    sim.step(render=False);robot.update(dt)
                    for obj in payload.values():obj.update(dt)
                projected=quat_apply_inverse(robot.data.root_quat_w,base.gravity)
                tilt_sq=projected[:,:2].square().sum(-1)
                tracking=torch.exp(-(robot.data.root_lin_vel_b[:,:2]-commands[:,:2]).square().sum(-1)/.1)
                displacement=torch.zeros(n,device=device);object_tilt=torch.zeros(n,device=device)
                drop=torch.zeros(n,dtype=torch.bool,device=device)
                for name,obj in payload.items():
                    relative=quat_apply_inverse(robot.data.root_quat_w,obj.data.root_pos_w-robot.data.root_pos_w)
                    reference=torch.tensor(payload_config[name]['center'],device=device)
                    displacement+=(relative[:,:2]-reference[:2]).square().sum(-1)
                    q=obj.data.root_quat_w;object_tilt+=(2*(q[:,1].square()+q[:,2].square())).clamp(0,2)
                    drop|=relative[:,2] < .1575-payload_config['development_thresholds']['drop_below_tray_m']
                fall=(projected[:,2]>-.5)|(robot.data.root_pos_w[:,2]<.25)
                rate=(residual-previous).square().sum(-1)
                energy=(robot.data.applied_torque*robot.data.joint_vel).abs().sum(-1)
                reward=tracking-3*tilt_sq-10*displacement-2*object_tilt-.02*rate-.00002*energy-5*(fall|drop)
                assert torch.isfinite(reward).all()
                episode_steps+=1;previous.copy_(residual)
                timeout=episode_steps>=400;terminated=fall|drop;done=terminated|timeout
                terminal_obs=observations()
                next_value=model.value(terminal_obs)
                for key,tensor in [('obs',obs),('action',action),('logprob',logprob),('value',value),
                    ('next_value',next_value),('reward',reward),('terminated',terminated),('done',done)]:
                    buffers[key].append(tensor.clone())
                reward_terms.append(torch.stack([tracking.mean(),tilt_sq.mean(),displacement.mean(),object_tilt.mean(),rate.mean(),energy.mean()]))
                if done.any():
                    completed+=int(done.sum());falls+=int(fall.sum());drops+=int(drop.sum());timeouts+=int((timeout&~terminated).sum())
                    reset(done.nonzero().flatten())
                obs=observations()
        b={k:torch.stack(v) for k,v in buffers.items()}
        adv,returns=advantages(b['reward'],b['value'],b['next_value'],b['terminated'],b['done'])
        stats=update(model,optimizer,b['obs'],b['action'],b['logprob'],returns,adv)
        report['environment_steps']+=n*args.horizon;report['physics_steps']+=args.horizon*10
        report['optimizer_steps']+=stats['optimizer_steps'];report['iterations_completed']=iteration+1
        report.update(status='training',episodes_completed=completed,falls=falls,payload_drops=drops,timeouts=timeouts,
                      elapsed_training_s=time.monotonic()-start)
        row=dict(iteration=iteration+1,environment_steps=report['environment_steps'],
            reward_mean=float(b['reward'].mean()),reward_component_means=torch.stack(reward_terms).mean(0).tolist(),
            component_names=['tracking','body_tilt_squared','payload_displacement_squared','payload_tilt','action_rate','energy_proxy'],
            episodes=completed,falls=falls,drops=drops,timeouts=timeouts,elapsed_s=report['elapsed_training_s'],**stats)
        # Cumulative optimizer count stays separate from this iteration's count.
        row['optimizer_steps_total']=report['optimizer_steps']
        with metrics.open('a') as f:f.write(json.dumps(row)+'\n')
        if (iteration+1)%10==0 or iteration+1==args.iterations:
            report['latest_checkpoint_sha256']=checkpoint(f'iteration-{iteration+1:04d}.pt')
        save_manifest();print(json.dumps(row),flush=True)
    report.update(status='trained',finished_at_utc=datetime.now(timezone.utc).isoformat(),
                  final_parameter_sha256=parameter_hash(),
                  parameter_change_l2=float(torch.sqrt(sum((value-initial_parameters[name]).square().sum()
                      for name,value in model.named_parameters())).detach()),
                  final_checkpoint_sha256=checkpoint('final.pt'),base_actor_sha256_after=hashfile(basepath))
    assert report['base_actor_sha256_after']==report['base_actor_sha256']
    assert report['optimizer_steps']>0 and report['environment_steps']>0
except Exception as exc:
    report.update(status='failed',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc())
    raise
finally:
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    save_manifest();print(json.dumps(report,indent=2),flush=True)
    if app is not None:app.close(wait_for_replicator=False,skip_cleanup=True)
