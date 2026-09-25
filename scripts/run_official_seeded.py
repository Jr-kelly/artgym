"""Run an unmodified official entry point with recorded deterministic RNG seeds."""
import argparse
import os
from pathlib import Path
import random
import runpy
import sys

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('entry', type=Path)
    args, rest = parser.parse_known_args()
    entry = args.entry.resolve()
    os.chdir(entry.parent)
    sys.path.insert(0, str(entry.parent))
    random.seed(args.seed)
    np.random.seed(args.seed)
    if entry.parent.name == 'func_lygra':
        # urdfpy 0.0.22 uses aliases removed by NumPy 1.24; preserve their types.
        for name, value in [('float',float),('int',int),('bool',bool),('complex',complex),('object',object)]:
            if name not in np.__dict__:setattr(np,name,value)
        import torch
        torch.manual_seed(args.seed)
        from scripts_official_adapter import install_adapters
        install_adapters(entry.parent.parent)
    sys.argv = [str(entry)] + rest
    runpy.run_path(str(entry), run_name='__main__')


if __name__ == '__main__':
    main()
