"""Known plan/clock-only hand reference for offline learned-acquisition replay.

Matches native close_motor/hold_motor for plain grasp plans. No current object,
contact, force, physical ID, or future recorded issued target is consulted.
"""
import numpy as np

def smooth(x):
    x=np.clip(x,0.,1.)
    return x*x*x*(10.-15.*x+6.*x*x)

def hand_reference(plan,t):
    assert plan is not None and t>=5.
    closed=np.asarray(plan['close_q'],dtype=float)
    if t<8.:
        u=(t-5.)/3.
        if 'close_waypoints' not in plan:
            opened=np.asarray(plan['open_q'],dtype=float)
            return opened+smooth(u)*(closed-opened)
        rows=plan['close_waypoints']
        for first,last in zip(rows[:-1],rows[1:]):
            if u<=last['fraction']:
                alpha=smooth((u-first['fraction'])/(last['fraction']-first['fraction']))
                return np.asarray(first['q'])*(1-alpha)+np.asarray(last['q'])*alpha
        return closed
    interval=plan.get('post_lift_preload_seconds')
    if t<12. or not interval:
        return closed
    first,last=interval
    alpha=smooth((t-first)/(last-first))
    operating=np.asarray(plan.get('post_lift_close_q',closed))
    bump=np.asarray(plan.get('post_lift_preparation_joint_bump_rad',[0.]*20))
    return closed+alpha*(operating-closed)+np.sin(np.pi*alpha)*bump
