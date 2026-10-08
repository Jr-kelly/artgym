"""Same-episode continuation of acquired pickup with live pose/history adaptation.

Saved short paths are motor priors only. No physics states/contact caches are
loaded into the simulator. Every stage starts from the current measured pose and
previously issued motor targets and records how far it differs from its prior.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.wuji_direct_pickup import DirectPickup, smooth
from scripts.wuji_direct_thumb_servo import DirectThumbServo

class DirectRoute:
    def __init__(self, spec, output):
        self.s=spec; self.output=Path(output); self.pickup=DirectPickup(spec,self.output)
        self.k=G2Kinematics(); self.stage_index=-1; self.runtime=None
        self.log=self.output/'direct-route-stage-observations.jsonl'
        self.stages=spec['continuous_stages']

    def command(self, elapsed, O, arm, hand, issued_arm, issued_hand, slider=None):
        if elapsed < self.s['duration_s']:
            return self.pickup.command(elapsed,O,arm,hand,issued_arm,issued_hand)
        age=elapsed-self.s['duration_s']; index=0
        while index<len(self.stages)-1 and age>=self.stages[index]['duration_s']-1e-8:
            age-=self.stages[index]['duration_s']; index+=1
        stage=self.stages[index]
        if index != self.stage_index:
            prior=np.load(Path(stage['source'])/'takeover.npz')
            refO=transform(prior['object_state'][:3],prior['object_state'][3:7])
            motion=json.loads(Path(stage['motor']).read_text())
            required=motion.get('required_actual_source')
            if required is not None and Path(required).resolve()!=Path(stage['source']).resolve():
                raise ValueError('Stage motor prior and declared actual source disagree')
            self.runtime=dict(motion=motion, liveO=O.copy(), correction=O@np.linalg.inv(refO),
                live_arm=issued_arm.copy(), live_hand=issued_hand.copy(), seed=issued_arm.astype(float).copy(),
                hand_offset=issued_hand-prior['issued_target'][7:])
            if stage.get('whole_grip_gravity_transport'):
                from scripts.wuji_whole_grip_gravity_transport import WholeGripGravityTransport
                self.runtime['gravity_transport']=WholeGripGravityTransport(stage['whole_grip_gravity_transport'],self.output)
                self.runtime['captured_L']=np.linalg.inv(O)@self.k.forward(arm)
                self.runtime['captured_hand']=hand.astype(float).copy()
            if 'direct_material_carrier' in motion:
                from scripts.wuji_direct_material_carrier import DirectMaterialCarrier
                self.runtime['material_carrier']=DirectMaterialCarrier(motion['direct_material_carrier'],self.output)
            if 'direct_joint_path_tracking' in motion:
                from scripts.wuji_direct_joint_path_tracking import DirectJointPathTracking
                self.runtime['joint_path_tracking']=DirectJointPathTracking(motion['direct_joint_path_tracking'],self.output)
            if 'direct_primary_patch' in motion:
                from scripts.wuji_direct_primary_patch import DirectPrimaryPatch
                self.runtime['primary_patch']=DirectPrimaryPatch(motion['direct_primary_patch'],self.output)
            if 'direct_material_carriers' in motion:
                from scripts.wuji_direct_material_carrier import DirectMaterialCarrierGroup
                self.runtime['material_carrier']=DirectMaterialCarrierGroup(motion['direct_material_carriers'],self.output)
            if 'direct_idle_middle_clearance' in motion:
                from scripts.wuji_direct_idle_middle_clearance import DirectIdleMiddleClearance
                self.runtime['idle_middle_clearance']=DirectIdleMiddleClearance(motion['direct_idle_middle_clearance'],self.output)
            if 'direct_thumb_servo' in motion:
                self.runtime['servo']=DirectThumbServo(motion['direct_thumb_servo'],self.output)
            elif 'direct_live_ring' in motion:
                from scripts.wuji_direct_live_ring import DirectLiveRing
                self.runtime['servo']=DirectLiveRing(motion['direct_live_ring'],self.output)
            else:
                if 'direct_pressure_path_servo' in motion:
                    from scripts.wuji_direct_pressure_path_servo import DirectPressurePathServo
                    self.runtime['pressure_servo']=DirectPressurePathServo(motion,self.output)
                if 'direct_grip_roll_servo' in motion:
                    from scripts.wuji_direct_grip_roll_servo import DirectGripRollServo
                    self.runtime['grip_roll_servo']=DirectGripRollServo(motion['direct_grip_roll_servo'],self.output)
                rows=motion['rows']; tt=np.array([r['time_s'] for r in rows])
                self.runtime.update(times=tt, arms=np.array([r['arm_q'] for r in rows]),
                                    hands=np.array([r['hand_q'] for r in rows]))
                initial_goal=self.runtime['correction']@self.k.forward(self.runtime['arms'][0])
                self.runtime['initial_alignment']=self.k.forward(issued_arm)@np.linalg.inv(initial_goal)
                self.runtime['live_wrist']=self.k.forward(issued_arm)
                self.runtime['prior_start_wrist']=self.k.forward(self.runtime['arms'][0])
            observation=dict(elapsed_s=float(elapsed),stage=stage['name'],stage_index=index,
                pose_source='sim_oracle live stage; independent pickup bias if configured',
                actual_object_world=O.tolist(),actual_arm_q=arm.tolist(),actual_hand_q=hand.tolist(),
                previously_issued_arm=issued_arm.tolist(),previously_issued_hand=issued_hand.tolist(),
                reference_source=stage['source'],motor_prior=stage['motor'],
                reference_actual_hand_delta_rad=(hand-prior['robot_q'][7:]).tolist(),
                reference_relative_wrist_delta_m=float(np.linalg.norm((np.linalg.inv(O)@self.k.forward(arm))[:3,3]-(np.linalg.inv(refO)@self.k.forward(prior['robot_q'][:7]))[:3,3])),
                physical_state_resets=0,scope='Reference state read only for adapting motor prior, never simulator initialization')
            with self.log.open('a') as f:f.write(json.dumps(observation)+'\n')
            self.stage_index=index
        state=self.runtime
        hand_offset=state['hand_offset'].copy()
        decay_indices=stage.get('hand_offset_decay_joint_indices',[])
        if decay_indices:
            # A newly acquired contact needs its planned posture. Retaining
            # an old posture delta through the acquisition can consume its
            # joint reserve. Keep entry continuity, then retire selected deltas.
            hand_offset[decay_indices]*=1-smooth(age/stage['hand_offset_decay_s'])
        if 'servo' in state:
            aq,hq=state['servo'].command(age,O,arm,hand,issued_arm,issued_hand,slider)
            if 'primary_patch' in state:
                hq=state['primary_patch'].correct(age,O,arm,hand,issued_hand,hq,slider)
            if 'material_carrier' in state:
                hq=state['material_carrier'].correct(age,O,arm,hand,issued_hand,hq,slider)
            if 'idle_middle_clearance' in state:
                hq=state['idle_middle_clearance'].correct(age,O,arm,hand,issued_arm,issued_hand,aq,hq,slider)
            return aq,hq
        refarm=np.array([np.interp(age,state['times'],state['arms'][:,j]) for j in range(7)])
        refhand=np.array([np.interp(age,state['times'],state['hands'][:,j]) for j in range(20)])
        if stage.get('fixed_acquired_motor_reference',False):
            # Acquired cap entry/stroke uses this episode's issued wrist and
            # supporting targets. A constant prior must not fade toward a
            # different recorded wrist/knife relation at the stage boundary.
            aq=state['live_arm'].copy()
            hq=refhand+hand_offset
            if 'primary_patch' in state:
                hq=state['primary_patch'].correct(age,O,arm,hand,issued_hand,hq,slider)
            if 'joint_path_tracking' in state:
                hq=state['joint_path_tracking'].correct(age,hand,hq)
            if 'pressure_servo' in state:
                aq,hq=state['pressure_servo'].correct(age,O,arm,hand,issued_arm,issued_hand,slider,aq,hq)
            return aq,hq
        goal=state['correction']@self.k.forward(refarm)
        # Reconcile motor preload at entry, then use observed knife coordinates.
        u=1-smooth(age/2.); alignment=state['initial_alignment']
        A=transform(alignment[:3,3]*u,Rotation.from_rotvec(Rotation.from_matrix(alignment[:3,:3]).as_rotvec()*u).as_quat())
        goal=A@goal
        if stage.get('preserve_actual_grip',False):
            # A flip rotates the grip that was actually acquired; it must not
            # erase that grip by fading toward an old knife/wrist transform.
            goal=state['live_wrist']@np.linalg.inv(state['prior_start_wrist'])@self.k.forward(refarm)
        if 'world_translation_m' in stage:
            # A loaded vertical lift starts at this episode's acquired wrist,
            # retaining its orientation and translating in world coordinates.
            goal=state['live_wrist'].copy()
            if stage.get('world_rotation_degrees'):
                # Rotate the acquired grip around this episode's knife axis
                # while lifting. This changes motor pose only; the knife is
                # never repositioned or constrained in physics.
                axis=state['liveO'][:3,:3]@np.array(stage['world_rotation_axis_knife'])
                axis=axis/np.linalg.norm(axis)
                fraction=smooth(age/stage['world_rotation_duration_s'])
                if stage.get('world_rotation_fraction_rows'):
                    timetable=np.array(stage['world_rotation_fraction_rows'])
                    fraction=float(np.interp(age,timetable[:,0],timetable[:,1]))
                angle=np.deg2rad(stage['world_rotation_degrees'])*fraction
                R=Rotation.from_rotvec(axis*angle).as_matrix()
                pivot=state['live_wrist'][:3,3] if stage.get('world_rotation_pivot')=='wrist' else state['liveO'][:3,3]
                goal[:3,3]=pivot+R@(goal[:3,3]-pivot)
                goal[:3,:3]=R@goal[:3,:3]
            goal[:3,3]+=np.array(stage['world_translation_m'])*smooth((age-stage.get('world_translation_start_delay_s',0.))/stage['world_translation_duration_s'])
        free_roll=stage.get('roll_free_position',False)
        aq,diagnostic=self.k.solve_near(goal,state['seed'],max_step=.12,
            minimum_margin=self.s.get('continuation_arm_command_margin_rad',self.s.get('arm_command_margin_rad',0.)),
            position_weight=.5 if free_roll else 4.,
            rotation_weight=2. if free_roll else 1.,
            posture_weight=.008 if free_roll else .003)
        if self.s.get('continuation_arm_command_margin_rad',self.s.get('arm_command_margin_rad')):
            with (self.output/'direct-route-arm-ik.jsonl').open('a') as f:
                f.write(json.dumps(dict(elapsed_s=float(elapsed),stage=stage['name'],
                    free_roll_position=free_roll,diagnostic=diagnostic,
                    scope='Motorreference reserve, original physical limits unchanged'))+'\n')
        state['seed']=aq.copy()
        hq=refhand+hand_offset
        if stage.get('hold_acquired_hand_targets',False):
            hq=state['live_hand'].copy()
        if 'gravity_transport' in state:
            if stage.get('gravity_rotation_fraction_rows'):
                timetable=np.array(stage['gravity_rotation_fraction_rows'])
                fraction=float(np.interp(age,timetable[:,0],timetable[:,1]))
                axis=state['liveO'][:3,:3]@np.array(stage['gravity_rotation_axis_knife'])
                R=Rotation.from_rotvec(axis*np.deg2rad(stage['gravity_rotation_degrees'])*fraction).as_matrix()
            hq=state['gravity_transport'].command(R,state['captured_L'],state['captured_hand'],state['live_hand'],state['liveO'][:3,:3])
        if 'primary_patch' in state:
            hq=state['primary_patch'].correct(age,O,arm,hand,issued_hand,hq,slider)
        if 'grip_roll_servo' in state:
            hq=state['grip_roll_servo'].correct(age,O,arm,hand,issued_hand,hq)
        if 'pressure_servo' in state:
            aq,hq=state['pressure_servo'].correct(age,O,arm,hand,issued_arm,issued_hand,slider,aq,hq)
        if 'material_carrier' in state:
            hq=state['material_carrier'].correct(age,O,arm,hand,issued_hand,hq,slider)
        if 'idle_middle_clearance' in state:
            hq=state['idle_middle_clearance'].correct(age,O,arm,hand,issued_arm,issued_hand,aq,hq,slider)
        hq=self.pickup.clear_loaded_middle(elapsed,O,arm,hand,issued_arm,issued_hand,aq,hq)
        return aq,hq
