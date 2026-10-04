"""Evaluation-only axial motor tracking and contact migration over two cycles.

The pad surface representative is a geometric indicator, not an observed
contact point. Live knife/wrist poses are used only by this offline analysis.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry


def analyze(trial,g):
    t=np.load(trial/'trace.npz');physics=json.loads((trial/'physics.json').read_text())
    plan=json.loads((trial/'plan.json').read_text())['args']
    cal=json.loads(Path(plan['handover_calibration']).read_text())
    normal=np.asarray(cal['object_in_wrist'])[:3,1]
    vertices=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']])
    def representative(q):
        m=g.w.forward(q)['hand_r_thumb_pad_link']
        v=vertices@m[:3,:3].T+m[:3,3]
        projection=v@normal;w=np.exp(-(projection-projection.min())/.0002)
        return (w[:,None]*v).sum(0)/w.sum()
    measured=np.array([representative(q) for q in t['q']])
    targets=np.array([representative(q) for q in t['target'][:,physics['hand_indices']]])
    wrist=Rotation.from_quat(t['wrist'][:,3:7]);obj=Rotation.from_quat(t['object'][:,3:7])
    def in_knife(point):return obj.inv().apply(wrist.apply(point)+t['wrist'][:,:3]-t['object'][:,:3])
    actual=in_knife(measured);issued=in_knife(targets)
    tracking=issued[:,2]-actual[:,2]
    normal_N=t['pair_slider_pressure_mean_N'][:,0]
    contact=t['pair_slider_contact_substep_fraction'][:,0]
    rel=wrist.inv()*obj;rows=[]
    for name,lo,hi in [('extend1',16,21),('return1',21,26),('extend2',26,31),('return2',31,36)]:
        ids=np.flatnonzero((t['time']>=lo)&(t['time']<hi))
        first=ids[:8];last=ids[-30:];i,j=ids[0],ids[-1]
        rows.append(dict(phase=name,
            issued_pad_representative_axial_displacement_mm=float((np.median(issued[last,2])-np.median(issued[first,2]))*1000),
            measured_pad_representative_axial_displacement_mm=float((np.median(actual[last,2])-np.median(actual[first,2]))*1000),
            rail_actual_phase_displacement_mm=float((np.median(t['slider'][last])-np.median(t['slider'][first]))*1000),
            axial_motor_tracking_mean_mm=float(np.mean(tracking[ids])*1000),
            axial_motor_tracking_last_mm=float(np.median(tracking[last])*1000),
            relative_seating_rotation_in_phase_rad=float((rel[i].inv()*rel[j]).magnitude()),
            actual_thumb_normal_mean_N=float(normal_N[ids].mean()),
            actual_thumb_contact_fraction=float(contact[ids].mean()),
            final_geometric_pad_transverse_offset_mm=(actual[last,:2].mean(0)*1000).tolist()))
    return dict(trial=str(trial),trace_sha256=hashlib.sha256((trial/'trace.npz').read_bytes()).hexdigest(),rows=rows),dict(time=t['time'],issued=issued,actual=actual,slider=t['slider'],normal=normal_N,contact=contact)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trial',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    g=DigitGeometry();rows=[];data=[]
    for trial in a.trial:
        r,d=analyze(trial,g);rows.append(r);data.append(d)
    scope='Live pose/contacts only offline evaluation. Surface representative follows actual authored pad and the same once-normal convention, but is not actual contact point/area or force. Phase displacements are signed movement, distinct from lower-referenced endpoints. Motor targets are actually issued finite-PD commands, not planned40mm alone.'
    (a.output/'phase-tracking.json').write_text(json.dumps(dict(scope=scope,trials=rows),indent=2)+'\n')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,1,figsize=(12,10),sharex=True)
    for trial,d in zip(a.trial,data):
        mask=d['time']>=16;clock=d['time'][mask];label=trial.name
        axes[0].plot(clock,(d['issued'][mask,2]-d['actual'][mask,2])*1000,label=label)
        axes[1].plot(clock,d['normal'][mask],label=label)
        axes[2].plot(clock,d['contact'][mask],label=label)
    for ax in axes:
        ax.grid(alpha=.25)
        for at in [21,26,31]:ax.axvline(at,color='gray',alpha=.4,linewidth=1)
    axes[0].set_ylabel('Issued minus measured\npad axial indicator (mm)');axes[0].legend(fontsize=8)
    axes[1].set_ylabel('A: actual thumb normal (N)');axes[2].set_ylabel('Actual pair contact fraction');axes[2].set_xlabel('Simulation clock (s)')
    fig.suptitle('Two-cycle motor tracking and actual contact\nGeometric pad indicator, not axial force or contact-area measurement')
    fig.tight_layout()
    for ext in ['png','pdf','svg']:fig.savefig(a.output/('directional-tracking.'+ext),dpi=160)
    print(json.dumps(rows))


if __name__=='__main__':main()
