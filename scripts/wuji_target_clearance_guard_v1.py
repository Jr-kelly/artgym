"""Constrain final issued thumb targets using name-based offline hand geometry.
No object state/contact/force/load inputs. Projection follows the actual prior
issued command; recorded action/history describes the command actually sent.
"""
import time,numpy as np
from scripts.g2_contact_geometry import DigitGeometry
class ThumbTargetClearanceGuard:
 def __init__(self,knife_spec):
  self.geometry=DigitGeometry(max_face_axes=10000,knife_spec=knife_spec);self.rows=[]
 def gap(self,q):
  g=self.geometry;gaps=g.self_gaps(q,'thumb')+g.pair_gaps(q,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')]);return min(r['gap_lower_bound_m'] for r in gaps)
 def project(self,previous,candidate,clock):
  start=time.monotonic();candidate=np.array(candidate,dtype=float);previous=np.array(previous,dtype=float);original=self.gap(candidate);result=candidate.copy();fraction=1.
  if original<.000015:
   anchor=candidate.copy();anchor[16:]=previous[16:]
   if self.gap(anchor)<.000015:
    # Support changes alone invalidate this point: retain prior whole command.
    if self.gap(previous)<.000015:raise RuntimeError('No previously certified issued target to project from')
    anchor=previous.copy()
   lo=0.;hi=1.
   # Segment subdivision rejects any intervening invalid command, then bisection.
   for u in np.linspace(.125,1.,8):
    test=anchor+u*(candidate-anchor)
    if self.gap(test)<.000025:hi=float(u);break
    lo=float(u)
   for _ in range(9):
    mid=(lo+hi)/2;test=anchor+mid*(candidate-anchor)
    if self.gap(test)>=.000025:lo=mid
    else:hi=mid
   result=anchor+lo*(candidate-anchor);fraction=lo
  final=self.gap(result);assert final>=.000015-1e-7
  self.rows.append(dict(clock_s=float(clock),candidate_gap_m=float(original),issued_gap_m=float(final),projection_fraction=float(fraction),wall_seconds=time.monotonic()-start))
  return result
