"""Common two-stage planner consuming only a labelled noisy initial observation.

Adapt the table pickup and lifted operation separately, preserving the existing
support targets while changing the index side contact after lift. This produces
motor targets, not collision certificates or constant forces.
"""
import copy,numpy as np
from scripts.plan_wuji_initial_geometry import adapt

def adapt_two_stage(estimate,pickup_plan,operating_plan,reference):
    pickup,pickup_pressure,unused,pickup_audit=adapt(estimate,pickup_plan,{'post_lift_target_q':pickup_plan['close_q']},reference,support_surface_scaling=True)
    operation,pressure,thumb,operation_audit=adapt(estimate,operating_plan,{'post_lift_target_q':operating_plan['close_q']},reference,support_surface_scaling=True)
    post=np.asarray(pickup['close_q']).copy();post[:4]=np.asarray(operation['close_q'])[:4]
    # Existing thumb/underside support preload is maintained across transfer.
    # The scheduled thumb path starts at the actual known final target.
    zero=np.asarray(thumb['rows'][0]['q_thumb']);anchor=post[16:]
    for row in thumb['rows']:row['q_thumb']=(anchor+np.asarray(row['q_thumb'])-zero).tolist()
    pickup.update(post_lift_close_q=post.tolist(),post_lift_preload_seconds=[12,14],post_lift_preparation_scope='Common noisy initial geometry IK; lower lateral index changes after actual pickup; no current truth or physical asset identity')
    thumb['support_preload_schedule']={'seconds':[12,14],'delta_q':(post-np.asarray(pickup['close_q'])).tolist()}
    thumb['known_motor_anchor']=True
    thumb['all_feasible_scope']='Estimated IK accuracy only; adapted original motor self/table geometry must be checked separately before native execution'
    return dict(estimate=copy.deepcopy(estimate),motor_plan=pickup,support_target_q=post.tolist(),thumb_reference=thumb,audit={'pickup':pickup_audit,'operation':operation_audit,'scope':'No physical asset/current object/contact read; geometric target preparation only'})
