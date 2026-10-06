"""Repaired full-flat G2/Wuji simulation with shared local adaptation.

Inactive digits park clear, the acquired pose corrects the clamp path once,
unused ring flexion eases after regrasp, and the operating normal reference
accounts for the observed traction regression. Finite original physics remains.
"""
import argparse,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',choices=['nominal','placement-error','placement-error-opposite','load125','mid-geometry'],default='nominal')
    p.add_argument('--no-video',action='store_true')
    a=p.parse_args()
    command=[sys.executable,'-m','scripts.run_wuji_flat_connected','--output',str(a.output),'--case',a.case,'--action-quality','--postpush-clamp-adaptation','--operation-normal-reference','1.4']
    if a.no_video:command.append('--no-video')
    raise SystemExit(subprocess.call(command))

if __name__=='__main__':main()
