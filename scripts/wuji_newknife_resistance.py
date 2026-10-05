"""Single passive capacity generator. Reference is user75gf working assumption.
No phase, task goal, clock, asset ID or controller input. Actual reaction unknown.
"""
import numpy as np
REFERENCE_N=.075*9.80665
def capacity(profile,q,v):
 base=float(profile.get('reference_N',REFERENCE_N))
 if profile['kind']=='constant':return base
 assert profile['kind']=='variable'
 # Mean sliding capacity reference; bounded +/-8% spatial modulation,
 # reverse running factor0.90. Rest capacity1.12 reference. All assumed.
 running=base*(1+.08*np.sin(2*np.pi*q/.018))*(.90 if v<0 else 1.)
 startup=base*1.12
 blend=np.exp(-(abs(v)/.002)**2)
 return float(max(0.,running*(1-blend)+startup*blend))
def distribution(profile):
 return [dict(q_rel_m=float(q),v_m_s=float(v),capacity_N=capacity(profile,q,v)) for q in np.linspace(-.010,.055,131) for v in [-.01,-.002,0,.002,.01]]
