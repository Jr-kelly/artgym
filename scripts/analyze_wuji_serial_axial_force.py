"""Aligned diagnostic axial measurements with explicit contact/clearance/endstop validity."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);a=p.parse_args();cal=json.loads(a.calibration.read_text());assert cal['passed'] and any(r.get('moving_base') for r in cal['rows'])
 rows=[json.loads(l) for l in (a.trial/'serial-load-cell-physical-steps.jsonl').open()];contacts=[json.loads(l) for l in (a.trial/'wrap-contact-physical-steps.jsonl').open()];assert len(rows)==len(contacts);tr=np.load(a.trial/'trace.npz');times=np.array([r['time_s'] for r in rows]);force=np.array([r['inferred_all_external_cap_axial_N'] for r in rows]);valid=[];pressure=[]
 for r,c in zip(rows,contacts):
  assert abs(r['time_s']-c['time_s'])<1e-8
  partners=[z['hand_link'] for z in c['contacts'] if z['knife_link']=='link_1'];only=bool(partners) and all('_thumb_' in n for n in partners)
  if 'thumb_only_contact' in r:only=r['thumb_only_contact']
  # Older diagnostic files log all hand/cap pairs but not table pairs. Conservative height guard excludes any cap/ground/table contact (original cap/rail envelope <40mm).
  clear=c['knife_world'][2]>.80;valid.append(only and clear and r['valid_no_cell_endstop']);pressure.append(np.interp(r['time_s'],tr['time'],tr['pair_slider_pressure_mean_N'][:,0]))
 valid=np.array(valid);pressure=np.array(pressure);pos=np.interp(times,tr['time'],tr['slider']);vel=np.interp(times,tr['time'],tr['slider_velocity']);plan=json.loads((a.trial/'plan.json').read_text());asset=Path(plan['args']['knife_asset']);import xml.etree.ElementTree as ET;lower=float(ET.parse(asset).find('.//joint[@name="slider"]/limit').get('lower'));pos-=lower
 if all('rail_guide_position_m' in r for r in rows):pos=np.array([r['rail_guide_position_m'] for r in rows]);vel=np.array([r['rail_guide_velocity_m_s'] for r in rows])
 cell_q=np.array([r['cell_q_m'] for r in rows]);cap_pos=pos+cell_q
 out=[]
 for label,start,direction in [('extend1',16,1),('return1',21,-1),('extend2',26,1),('return2',31,-1)]:
  for part,lo,hi in [('startup',start,start+.5),('mid',start+.5,start+3.5),('nearend',start+3.5,start+5)]:
   selected=(times>=lo)&(times<hi);m=selected&valid;moving=m&(direction*vel>.001)
   d=dict(phase=label,part=part,window_s=[lo,hi],valid_fraction=float(valid[selected].mean()),valid_samples=int(m.sum()),pressure_normal_mean_N=float(pressure[m].mean()) if m.any() else None,rail_guide_position_minmax_mm=[float(pos[m].min()*1000),float(pos[m].max()*1000)] if m.any() else None,diagnostic_cap_axial_position_minmax_mm=[float(cap_pos[m].min()*1000),float(cap_pos[m].max()*1000)] if m.any() else None,velocity_minmax_mm_s=[float(vel[m].min()*1000),float(vel[m].max()*1000)] if m.any() else None,axial_signed_median_N=float(np.median(force[m])) if m.any() else None,axial_signed_minmax_N=[float(force[m].min()),float(force[m].max())] if m.any() else None,sustained_moving_directional_median_N=float(np.median(direction*force[moving])) if moving.any() else None,loaded_moving_samples=int(moving.sum()),peak_scope='Maximuminstantaneous samples mayinclude collisionimpulse/nearstall; not sustainedcapacity or realforce.')
   out.append(d)
 np.savez_compressed(a.trial/'diagnostic-axial-aligned.npz',time_s=times,diagnostic_axial_signed_N=force,valid=valid,pressure_normal_N=pressure,rail_guide_position_m=pos,diagnostic_cap_position_m=cap_pos,velocity_m_s=vel)
 report=dict(trial=str(a.trial),position_sampling_scope=('Full physics-rate measured rail coordinates' if all('rail_guide_position_m' in r for r in rows) else 'Rail guide position and velocity interpolated from30Hz trace; cell deflection is full physics-rate'),clock_window_scope='startup/mid/nearend refer to command clock windows, not detected breakaway. Instant peaks are not sustained force capacity.',kind='modified-series-elastic-diagnostic',original_task_direct_axial_measurement_completed=False,hardware_measurement_completed=False,calibration=str(a.calibration),calibration_sha256=hashlib.sha256(a.calibration.read_bytes()).hexdigest(),calibration_max_moving_fixture_residual_N=max(r['max_abs_residual_N'] for r in cal['rows']),equation='F_external_cap dot rail = m_cap * a_cap_world dot rail - m_cap * g_world dot rail - F_series_actually_applied; worldacceleration includesmovingbase. Attribution tothumb only if solecap-contactdigit and noendstop/ground.',attribution_scope='Currentdata: exactallcapcontactpartnerswhenavailable, otherwiseallhand/cappairsplusconservativeclearanceguard. Guard isbodyworldheight>.80m with tabletop.75m and cap<40mm envelope. Originalwithinobjectselfcollisionfilter1 matches successfulmovingcalibration.',rows=out)
 (a.trial/'diagnostic-axial-analysis.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
