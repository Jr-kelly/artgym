"""Record worker identity separately from the official entry point's status."""
import os
import runpy
import sys
from pathlib import Path
import json

if __name__=='__main__':
    args=sys.argv
    dataset=args[args.index('--dataset')+1];instance=args[args.index('--instance')+1]
    root=Path(__file__).resolve().parents[1]/'runs/experiment-suite/data'/dataset/instance
    root.mkdir(parents=True,exist_ok=True)
    (root/'worker.pid').write_text(str(os.getpid()))
    runpy.run_module('scripts.run_official_dataset',run_name='__main__')
