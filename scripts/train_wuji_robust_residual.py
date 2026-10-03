"""PPO pilot for meaningful load/contact behavior; resumable model/Adam/RNG.
Base R800 encoder, teacher actor and normalizer remain unchanged.
"""
import argparse,datetime,hashlib,json,signal,time
from pathlib import Path
from scripts.wuji_robust_learning import LearningSystem,ResidualActorCritic,TEACHER,R800
import torch,numpy as np
from omegaconf import OmegaConf
from scripts.wuji_student_interface import tensor_hash

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--envs',type=int,default=512);p.add_argument('--updates',type=int,default=400);p.add_argument('--horizon',type=int,default=32);p.add_argument('--seed',type=int,default=2026100307);p.add_argument('--randomization-scale',type=float,default=.5);p.add_argument('--load-max',type=float,default=.1);p.add_argument('--detent-max',type=float,default=.1);p.add_argument('--epochs',type=int,default=4);p.add_argument('--minibatch',type=int,default=4096);p.add_argument('--resume',type=Path)
    p.add_argument('--support-residual-scale',type=float,default=.25);p.add_argument('--rotation-cost',type=float,default=0.);p.add_argument('--wrist-nominal',type=Path);p.add_argument('--wrist-probability',type=float,default=.5)
    p.add_argument('--resample-initial-estimates',action='store_true',help='At episode reset only, draw another labelled noisy initial observation from same-geometry synthetic sensor bank; no actor asset ID')
    p.add_argument('--fresh-sampling-seed',type=int,help='Explicit matched freshoptimizer pilot samplingstream reset after differing inputlayer initialization; requires initialize-model-from')
    p.add_argument('--support-load-features',action='store_true',help='Append9 legal PD/FK/history model features: threeestimatednormal loads, settledreferences, torque residuals; no trueforce/contact input')
    p.add_argument('--support-delta-coordinates',choices=['joint','normal'],help='Matched bounded correction around frozen750 support actor; normal uses fixed initial estimatedFK basis, no forcefeedback')
    p.add_argument('--gae-lambda',type=float,default=.95,help='Explicit temporal credit horizon; identical across paired preparation pilots')
    p.add_argument('--support-latch-after-preparation',action='store_true',default=None,help='Support motor residual decision stops after known16s; thumb remains30Hz, actual history continues. Position retention is not constant force.')
    p.add_argument('--support-command-period',type=int,choices=[1,5],default=None,help='Default restores savedperiod onresume, otherwise1. Support decisions every1or5 known30Hz frames; thumb remains30Hz, jointdecision PPO log/KL masks excludeheld coordinates')
    p.add_argument('--reset-support-logstd',type=float,help='Explicit exploration curriculum: reset first16 logstd and their Adam moments only; preserve thumbvariance/means and allothermodel/Adam/RNG')
    p.add_argument('--freeze-thumb-prior',action='store_true',help='Preserve resumed deterministic thumb actor mapping on the same legal features; learn support outputs and exploration variance. Not constant physicalforce.')
    p.add_argument('--stable-progress-reward',action='store_true',help='Trainingrewardonly: remove primary reach bonus during operation outside original10mm/.25rad instantaneous body stability conditions; no actor/physics/criteria change')
    p.add_argument('--override-initial-estimate-scene',type=Path,help='Explicit curriculum change on resume: replace saved synthetic initial-observation bank while retaining model/Adam/RNG. Normal resume keeps saved scene; new physical episodes only.')
    p.add_argument('--proprioceptive-pressure-config',type=Path,help='Legal FK/joint-issuedtarget pressureproxy, shared analytic native/batch controller; no force/contact truth');p.add_argument('--training-asset-registry',type=Path,help='Registered train-only physical assets; IDs select simulator loading, never actor/controller');p.add_argument('--initial-estimate-scene',type=Path,help='Transparent noisy once-initial observations and common IK motor plans, actor-visible estimated geometry only; no live truth');p.add_argument('--training-geometry-schedule',type=Path,help='ActualG2 physicalsampling only: registeredtraining IDs perenv, never actorinputs or heldout assets');p.add_argument('--object',default='knife_wuji_robust_family_20261003');p.add_argument('--actual-hold-history',type=int,choices=[0,50],default=50)
    p.add_argument('--thumb-slider-reward',type=float,default=0.)
    p.add_argument('--thumb-residual-scale',type=float,default=.75);p.add_argument('--contact-progress-reward',type=float,default=0.)
    p.add_argument('--handover-profiles',type=Path)
    p.add_argument('--base-mode',choices=['r800','zero','geometric'],default='r800')
    p.add_argument('--takeover-seconds',type=float,default=16.,help='Actual G2 learned lift/hold begins8–16s; operation remains16s, original50 actual history and physical continuity');p.add_argument('--thumb-reference',type=Path);p.add_argument('--scene',choices=['proxy','g2'],default='proxy')
    p.add_argument('--strong-slider-contact-reward',action='store_true',help='Trainingrewardonly: require slider netcontact force inadditiontothumb proximity/netcontact; old completion criterion unchanged');p.add_argument('--absorbing-failure-penalty',action='store_true',help='ActualG2 training: terminal-8 plus discounted-1 reward per remaining36s controlframe, correcting truncation incentive; physicalcriteria unchanged');p.add_argument('--bounded-actor-update',action='store_true',help='Separate actor/critic clipping; damp each actor Adam proposal to analytic KL<=.03 over every active sample in the current actual rollout');p.add_argument('--functional-thumb-reward',action='store_true',help='ActualG2: use slider-proximity/netcontact proxy instead of rewarding thumb contact with anybody; trainingrewardonly');p.add_argument('--active-kl-stop',action='store_true',help='Stop PPOepochs using only samples where the residual actually controls; preserve legacy all-sample KL separately');p.add_argument('--history-features',action='store_true',help='Append frozen SC16D encoding of the existing legal2076 input; actual G2 only, no additional sensors/truth');p.add_argument('--load-profile',choices=['sinusoidal','triangular','pulse','constant','mixed'],default='sinusoidal');p.add_argument('--load-frequency',type=float,default=1.7);p.add_argument('--action-parameterization',choices=['incremental','bounded-motor-offset'],default='incremental');p.add_argument('--initialize-model-from',type=Path,help='Fresh optimizer/RNG pilot initialized from matching model; bounded-offset mode resets actor output head');p.add_argument('--resistance-integration',choices=['legacy-explicit','solver-brake'],default='legacy-explicit');p.add_argument('--load-min',type=float,default=0.);p.add_argument('--detent-min',type=float,default=0.);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    load_feature_spec=torch.load(a.resume,map_location='cpu').get('support_load_feature_spec') if a.resume else None
    if a.support_load_features and load_feature_spec is None:load_feature_spec=dict(format='legal-support-load-features-v1',dimensions=9,fields=['estimated_normal_load_3','settled_reference_load_3','unexplained_torque_fraction_3'],scope='KnownPD, measuredq/fiveframehistory, onceinitialestimatedknife normal; no actualforce/contact identity or currentobjecttruth; engineeringassumption not confirmedhardware calibration')
    if load_feature_spec is not None:assert a.scene=='g2' and not a.history_features
    if a.support_command_period is None:
        a.support_command_period=torch.load(a.resume,map_location='cpu').get('support_command_period',1) if a.resume else 1
    assert a.support_command_period in [1,5]
    assert 0<a.gae_lambda<=1
    if a.support_latch_after_preparation is None:a.support_latch_after_preparation=torch.load(a.resume,map_location="cpu").get("support_latch_after_preparation",False) if a.resume else False
    if a.support_latch_after_preparation:assert a.scene=="g2" and a.takeover_seconds<16
    torch.set_num_threads(4);torch.manual_seed(a.seed);np.random.seed(a.seed)
    wrist=json.loads(a.wrist_nominal.read_text())['wrist_quaternion_xyzw'] if a.wrist_nominal else None
    support_spec=torch.load(a.resume,map_location='cpu').get('support_estimator_spec') if a.resume else None
    if a.scene=='g2':
        from scripts.g2_continuous_scene import G2ContinuousScene
        assert a.base_mode=='geometric' and a.actual_hold_history==50 and a.thumb_reference is not None
        training_instances=None;asset_registry=None
        if a.training_asset_registry:
            registry=json.loads(a.training_asset_registry.read_text());assert all(row['split']=='train' for row in registry['entries'])
            asset_registry={row['instance']:row['directory'] for row in registry['entries']}

        if a.training_geometry_schedule:
            schedule=json.loads(a.training_geometry_schedule.read_text());training_instances=schedule['instances']
            manifest=json.loads((Path('research/robust-knife-family-20261003')/'dense-family-v1/manifest.json').read_text())
            allowed=set(asset_registry) if asset_registry is not None else {r['instance'] for r in manifest['entries'] if r['split']=='train'}
            assert len(training_instances)==a.envs and set(training_instances)<=allowed
        scene_spec=torch.load(a.resume,map_location='cpu').get('scene_spec') if a.resume else json.loads(a.initial_estimate_scene.read_text()) if a.initial_estimate_scene else None
        if a.override_initial_estimate_scene:
            assert a.resume and a.initial_estimate_scene is None, 'Use explicit resume curriculum override alone'
            scene_spec=json.loads(a.override_initial_estimate_scene.read_text())
        system=G2ContinuousScene(a.envs,a.seed,a.randomization_scale,instances=training_instances,load_max=a.load_max,detent_max=a.detent_max,contact_progress_reward=a.contact_progress_reward,reference_spec=json.loads(a.thumb_reference.read_text()),support_scale=a.support_residual_scale,thumb_scale=a.thumb_residual_scale,takeover_seconds=a.takeover_seconds,load_profile=a.load_profile,load_frequency=a.load_frequency,history_features=a.history_features,support_estimator_spec=support_spec,functional_thumb_reward=a.functional_thumb_reward,absorbing_failure_penalty=a.absorbing_failure_penalty,strong_slider_contact_reward=a.strong_slider_contact_reward,action_parameterization=a.action_parameterization,resistance_integration=a.resistance_integration,load_min=a.load_min,detent_min=a.detent_min,scene_spec=scene_spec,asset_registry=asset_registry,resample_initial_estimates=a.resample_initial_estimates,stable_progress_reward=a.stable_progress_reward,support_load_feature_spec=load_feature_spec,proprioceptive_pressure_spec=json.loads(a.proprioceptive_pressure_config.read_text()) if a.proprioceptive_pressure_config else None)
        (a.output/'scene.json').write_text(json.dumps(dict(platform='G2+Wuji v1',scope='Actual continuous tabletop acquisition and operation; resets only at new episode boundaries',prefix_control_frames=system.takeover_frame,actual_history_frames=50,physics_hz=240,control_hz=30,stable_progress_reward=a.stable_progress_reward,stable_progress_reward_scope='Remove only primary reach bonus outside instantaneous originalbody stability thresholds; originalfull-episode maximum criteria and termination unchanged; simulatortruth rewardonly',geometry_slots=system.instances,resistance_integration=a.resistance_integration,load_range_N=[a.load_min,a.load_max] if a.resistance_integration=='solver-brake' else [0,a.load_max*a.randomization_scale],detent_range_N=[a.detent_min,a.detent_max] if a.resistance_integration=='solver-brake' else [0,a.detent_max*a.randomization_scale],policy_geometry_estimate=('Noisy once-initial geometric observation, common IK adaptation; no actor physicalasset ID/currentobjecttruth' if system.estimated_plans else 'Same nominal geometry and fixed offline prior for every instance'),scene_spec=system.scene_spec,load_profile=system.load_profile,load_frequency_rad_s=system.load_frequency,mixed_frequency_range_rad_s=[1.3,2.3] if system.load_profile=='mixed' else None,actor_inputs=f'{system.public_dim} measured/known public features,2076 frozenR800 encoder'+('; appended frozen16D legalhistory latent' if a.history_features else '')+'; no live object/slider/contact or assetID',critic=f'{system.public_dim+27} public+truth/contact/load, reward-only thumb proximity/contact proxy',joint_noise_std_rad=.002*a.randomization_scale,joint_bias_bound_rad=.006*a.randomization_scale,calibration_translation_bound_m=.001*a.randomization_scale,calibration_angle_bound_deg=1.5*a.randomization_scale,delay_probability=.15*a.randomization_scale,pickup_xy_error_bound_m=.001*a.randomization_scale,pickup_yaw_error_bound_deg=1.5*a.randomization_scale,friction_assumption={'hand':[.65,1.15],'knife':[1.8,3.4]},failure_training_objective='-8 plus discounted-1 per remainingframe' if a.absorbing_failure_penalty else 'legacy -8 on drop',pickup_reward_scope='For8--12s learnedlift only: physical objectretentionrelativewrist, critic/rewardonly; samelegalactorfeatures andnominalprior',effort='Original gains and total motor torque clipped to G2/Wuji URDF limits'),indent=2))
    else:
        assert not a.stable_progress_reward and not a.strong_slider_contact_reward and not a.absorbing_failure_penalty and not a.functional_thumb_reward and not a.history_features and support_spec is None,'History/support features currently audited only for actual G2'
        system=LearningSystem(a.envs,a.seed,a.randomization_scale,a.load_max,a.detent_max,support_scale=a.support_residual_scale,rotation_cost=a.rotation_cost,wrist_nominal=wrist,wrist_probability=a.wrist_probability,object_name=a.object,history_hold_frames=a.actual_hold_history,thumb_slider_reward=a.thumb_slider_reward,thumb_scale=a.thumb_residual_scale,contact_progress_reward=a.contact_progress_reward,handover_profiles=a.handover_profiles,base_mode=a.base_mode,thumb_reference=a.thumb_reference,load_profile=a.load_profile,load_frequency=a.load_frequency)
    device=system.env.device
    model=ResidualActorCritic(getattr(system,'public_dim',154),getattr(system,'public_dim',154)+27).to(device);opt=torch.optim.Adam(model.parameters(),lr=3e-4,eps=1e-5);start=0
    if a.initialize_model_from:
        assert not a.resume
        initial=torch.load(a.initialize_model_from,map_location=device)
        weights=initial['model']
        if initial.get('frozen_thumb_actor',False):
            assert weights['actor.0.weight'].shape==model.actor[0].weight.shape
            model.freeze_thumb_actor()
        if weights['actor.0.weight'].shape!=model.state_dict()['actor.0.weight'].shape:
            assert weights['actor.0.weight'].shape[1]==154 and model.state_dict()['actor.0.weight'].shape[1] in [170,163]
            extended=model.state_dict()
            for key,value in weights.items():
                if key=='actor.0.weight':extended[key].zero_();extended[key][:,:154]=value
                elif key=='critic.0.weight':extended[key].zero_();extended[key][:,:154]=value[:,:154];extended[key][:,getattr(system,'public_dim',154):]=value[:,154:]
                else:extended[key]=value
            weights=extended
        model.load_state_dict(weights)
        if a.action_parameterization=='bounded-motor-offset' and initial.get('action_parameterization','incremental')!='bounded-motor-offset':
            torch.nn.init.zeros_(model.actor[-1].weight);torch.nn.init.zeros_(model.actor[-1].bias)
    if a.resume:
        saved=torch.load(a.resume,map_location=device);assert saved.get('action_parameterization','incremental')==a.action_parameterization
        if saved.get('frozen_thumb_actor',False):model.freeze_thumb_actor()
        model.load_state_dict(saved['model']);opt.load_state_dict(saved['optimizer']);start=saved['updates']
        # map_location moves serialized RNG buffers too; generator APIs require CPU bytes.
        torch.set_rng_state(saved['rng_cpu'].cpu());torch.cuda.set_rng_state_all([state.cpu() for state in saved['rng_cuda']]);np.random.set_state(saved['rng_numpy'])
    if a.fresh_sampling_seed is not None:
        assert a.initialize_model_from and not a.resume
        torch.manual_seed(a.fresh_sampling_seed);np.random.seed(a.fresh_sampling_seed)
    delta_spec=torch.load(a.resume,map_location="cpu").get("support_delta_spec") if a.resume else None
    if a.support_delta_coordinates is not None:
        assert a.initialize_model_from and not a.resume and a.scene=="g2" and a.action_parameterization=="bounded-motor-offset" and not a.support_load_features and not a.history_features
        delta_spec=dict(mode=a.support_delta_coordinates,reference_actor_state={k:v.detach().cpu().clone() for k,v in model.actor.state_dict().items()},reference_weight_sha256=hashlib.sha256(a.initialize_model_from.read_bytes()).hexdigest(),scope="Fixed legal-input support actor plus boundedlearnedcorrection; initialestimatednormal/FK coordinatebasis, original.04rad supportspan and limits. No forcefeedback.")
        with torch.no_grad():model.actor[-1].weight[:16].zero_();model.actor[-1].bias[:16].zero_()
    if delta_spec is not None:
        from scripts.wuji_support_delta_coordinates import SupportDeltaCoordinates
        system.support_delta_coordinates=SupportDeltaCoordinates(delta_spec,a.envs,device)
    if a.freeze_thumb_prior:
        assert (a.resume or a.initialize_model_from) and a.scene=='g2' and a.action_parameterization=='bounded-motor-offset'
        model.freeze_thumb_actor()
    if a.support_command_period>1 or a.reset_support_logstd is not None:
        assert a.scene=='g2' and a.action_parameterization=='bounded-motor-offset'
    if a.reset_support_logstd is not None:
        assert (a.resume or a.initialize_model_from) and -3.5<=a.reset_support_logstd<=-.4
        with torch.no_grad():model.logstd[:16].fill_(a.reset_support_logstd)
        for key in ['exp_avg','exp_avg_sq']:
            if key in opt.state[model.logstd]:opt.state[model.logstd][key][:16].zero_()
    from scripts.wuji_support_command_sampling import SupportCommandSampler,log_prob as decision_log_prob,entropy as decision_entropy
    sampler=SupportCommandSampler(a.envs,device,a.support_command_period,getattr(system,'takeover_frame',0),a.support_latch_after_preparation)
    (a.output/'config.yaml').write_text(OmegaConf.to_yaml(system.cfg,resolve=True));(a.output/'args.json').write_text(json.dumps(vars(a),default=str,indent=2))
    basehash=tensor_hash(system.player.model.state_dict());begin=time.monotonic();stopping=[False]
    for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,lambda *_:stopping.__setitem__(0,True))
    def save(u):
        assert tensor_hash(system.player.model.state_dict())==basehash
        payload=dict(support_delta_spec=delta_spec,support_latch_after_preparation=a.support_latch_after_preparation,support_load_feature_spec=load_feature_spec,support_command_period=a.support_command_period,support_decision_scope='Support heldbetween knownclock decisions; thumb30Hz; actualcommandhistory continuous; joint-event masked PPO/entropy/KL',frozen_thumb_actor=model.frozen_thumb_actor is not None,frozen_thumb_scope='Deterministic thumb mean from a frozen legal-input actor; support outputs and exploration variance remain trainable; not measuredforce control',format='wuji-r800-residual-ppo-v1',model=model.state_dict(),optimizer=opt.state_dict(),updates=u,transitions=system.transitions,args=vars(a),actor_inputs=('9 legal model supportfeatures; ' if load_feature_spec else '')+'111 legal public+20 issued+20 frozen base action+3 wrist gravity'+('+16 frozen legal history latent' if a.history_features else '')+(';8 frozen legal-input support estimates' if support_spec else '')+'; no current truth',critic_inputs='actor features+21 truth+5 contact+1 load',history_features=a.history_features,scene_spec=system.scene_spec if a.scene=='g2' else None,support_estimator_spec=system.support_estimator_spec if a.scene=='g2' else None,public_dim=getattr(system,'public_dim',154),proprioceptive_pressure_spec=system.proprioceptive_pressure_spec if a.scene=='g2' else None,action_scale=system.scale.tolist(),action_parameterization=a.action_parameterization,resistance_integration=a.resistance_integration,action_scale_units='radians about scheduled motor reference' if a.action_parameterization=='bounded-motor-offset' else 'normalized original incremental action',action_base_mode=system.base_mode,thumb_reference=system.reference_spec,teacher_sha256=hashlib.sha256(TEACHER.read_bytes()).hexdigest(),student_sha256=hashlib.sha256(R800.read_bytes()).hexdigest(),base_tensor_hash=basehash,rng_cpu=torch.get_rng_state(),rng_cuda=torch.cuda.get_rng_state_all(),rng_numpy=np.random.get_state(),resume='Optimizer/RNG restored; new physics episodes, no bitwise solver continuation')
        f=a.output/f'update_{u:06d}.pth';tmp=f.with_suffix('.tmp');torch.save(payload,tmp);tmp.replace(f);f.with_suffix('.sha256').write_text(hashlib.sha256(f.read_bytes()).hexdigest()+'\n')
    last=start
    try:
        for u in range(start+1,a.updates+1):
            public=[];critic=[];actions=[];logs=[];values=[];rewards=[];dones=[];active=[];old_means=[];old_scales=[];joint_events=[]
            for step in range(a.horizon):
                x,c=system.features()
                with torch.no_grad():
                    dist,value=model(x,c)
                    clock=system.age if a.scene=='g2' else torch.zeros(a.envs,device=device,dtype=torch.long)
                    action,event=sampler.sample(dist,clock);log=decision_log_prob(dist,action,event)
                joint_events.append(event)
                active.append(system.policy_active.clone())
                if a.bounded_actor_update:old_means.append(dist.mean.detach().clone());old_scales.append(dist.scale.detach().clone())
                reward,done=system.step(action)
                public.append(x);critic.append(c);actions.append(action);logs.append(log);values.append(value);rewards.append(reward);dones.append(done)
            with torch.no_grad():
                # Bootstrap without advancing frozen actor RNN a second time.
                next_public,next_critic=system.features();_,nv=model(next_public,next_critic)
            v=torch.stack(values);r=torch.stack(rewards);d=torch.stack(dones);adv=torch.zeros_like(r);gae=torch.zeros(a.envs,device=device)
            for t in reversed(range(a.horizon)):
                nextv=nv if t==a.horizon-1 else v[t+1];live=(~d[t]).float();delta=r[t]+.995*nextv*live-v[t];gae=delta+.995*a.gae_lambda*live*gae;adv[t]=gae
            returns=(adv+v).flatten();advantages=adv.flatten();advantages=(advantages-advantages.mean())/(advantages.std()+1e-8)
            px=torch.stack(public).flatten(0,1);cx=torch.stack(critic).flatten(0,1);ac=torch.stack(actions).flatten(0,1);lp=torch.stack(logs).flatten();eligible=torch.stack(active).flatten();events=torch.stack(joint_events).flatten(0,1);losses=[];kls=[];active_kls=[];bounded_updates=[]
            if a.bounded_actor_update:
                from scripts.wuji_bounded_actor_update import bounded_step
                old_mean=torch.stack(old_means).flatten(0,1);old_scale=torch.stack(old_scales).flatten(0,1)
            for epoch in range(a.epochs):
                for ids in torch.randperm(len(px),device=device).split(a.minibatch):
                    dist,value=model(px[ids],cx[ids]);newlog=decision_log_prob(dist,ac[ids],events[ids]);ratio=(newlog-lp[ids]).exp();mask=eligible[ids].float();denom=mask.sum().clamp_min(1)
                    piloss=-(torch.minimum(ratio*advantages[ids],ratio.clamp(.8,1.2)*advantages[ids])*mask).sum()/denom;vloss=.5*(value-returns[ids]).square().mean();loss=piloss+.5*vloss-.001*(decision_entropy(dist,events[ids])*mask).sum()/denom
                    opt.zero_grad(set_to_none=True);loss.backward()
                    if a.bounded_actor_update:bounded_updates.append(bounded_step(model,opt,px,old_mean,old_scale,eligible,joint_events=events))
                    else:torch.nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
                    losses.append(float(loss));divergence=(ratio-1)-(newlog-lp[ids]);kls.append(float(divergence.mean()));active_kls.append(float((divergence*mask).sum()/denom))
                if np.mean((active_kls if a.active_kl_stop else kls)[-max(1,len(px)//a.minibatch):])>.03:break
            recent=system.stats[-min(128,len(system.stats)):]
            row=dict(support_command_period=a.support_command_period,support_decision_fraction=float(events[eligible,:16].float().mean()) if eligible.any() else 0.,support_logit_std_mean=float(model.logstd[:16].clamp(-3.5,-.4).exp().mean()),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),update=u,transitions=system.transitions,episodes=system.episodes,reward=float(r.mean()),loss=float(np.mean(losses)),kl=float(np.mean(kls)),active_sample_kl=float(np.mean(active_kls)),epoch_stop_kl_scope='active residual-control samples' if a.active_kl_stop else 'legacy all samples including scripted prefix',policy_active_fraction=float(eligible.float().mean()),actual_hold_history_frames=a.actual_hold_history,wall_seconds=time.monotonic()-begin,peak_extension_mean_m=float(np.mean([e['peak_extension_m'] for e in recent])) if recent else None,contact_mean=float(np.mean([e['thumb_contact_fraction'] for e in recent])) if recent else None,fall_fraction=float(np.mean([e['fall'] for e in recent])) if recent else None,scope='Training fitting/behavior only')
            if a.bounded_actor_update:
                row.update(analytic_active_rollout_kl=bounded_updates[-1]['analytic_active_rollout_kl'],actor_step_fraction_mean=float(np.mean([b['step_fraction'] for b in bounded_updates])),rejected_actor_updates=sum(not b['accepted'] for b in bounded_updates),actor_bound_scope='All active samples in current rollout; not a bound on future episodes')
            if a.scene=='g2':
                row.update(recent_episode_count=len(recent),recent_complete_fraction=float(np.mean([e['operation_complete'] for e in recent])) if recent else None,recent_pickup_valid_fraction=float(np.mean([e['pickup_valid'] for e in recent])) if recent else None,all_complete_count=sum(e['operation_complete'] for e in system.stats),all_pickup_valid_count=sum(e['pickup_valid'] for e in system.stats),failure_counts={name:sum(e['failure']==name for e in recent) for name in ['pickup/hold','body unstable/drop','extension','retraction','thumb-contact']},behavior_scope='Training samples, last128 episodes may mix early failures and complete36s trajectories; never independent validation')
            with (a.output/'learning.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            print(json.dumps(row),flush=True);last=u
            if u%50==0 or u==a.updates or stopping[0]:save(u)
            if stopping[0]:break
        (a.output/'training-episodes.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in system.stats));(a.output/'complete.json').write_text(json.dumps(row,indent=2))
    finally:
        if last>start and not (a.output/f'update_{last:06d}.pth').exists():save(last)
        system.close()
if __name__=='__main__':main()
