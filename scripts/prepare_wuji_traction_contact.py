"""Geometry-only contact registration and existing continuous path certificates."""
import argparse,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--lateral-site',type=float,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base='runs/wrap-force-20261004/planning/source-bounded-index-wrap-v8/direct-corner-v6/'
    out=str(a.output)
    commands=[['scripts.plan_wuji_thumb_registration','--plan',base+'motor-plan.json','--lateral-site',str(a.lateral_site),'--virtual-inset','.0022','--output',out],
        ['scripts.plan_g2_direct_thumb_motor_stroke','--plan',out+'/motor-plan.json','--output',out+'/reference.json','--lateral-relief','0'],
        ['scripts.audit_wuji_actual_acquisition_motor','--plan',out+'/motor-plan.json','--acquisition',base+'acquisition/acquisition-path.json','--table-y','-.23','--output',out+'/closure-audit.json'],
        ['scripts.audit_g2_anchored_thumb_motor','--reference',out+'/reference.json','--motor-plan',out+'/motor-plan.json','--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','81','--output',out+'/full-stroke-audit.json']]
    for command in commands:subprocess.run([sys.executable,'-m']+command,check=True)
if __name__=='__main__':main()
