"""Stdlib launcher: reuse the saved private environment in every field terminal."""
import json
import os
from pathlib import Path
import sys


def main():
    arguments=sys.argv[1:]
    path=Path('field-session.json')
    if '--config' in arguments:path=Path(arguments[arguments.index('--config')+1])
    c=json.loads(path.read_text())
    if c.get('format')!='wuji-rear-launch-v1':raise ValueError('Unknown field launch configuration')
    entry=Path(c['private_root'])/'rear_field.py'
    if not entry.is_file():raise FileNotFoundError('Install the matching private delivery: '+str(entry))
    environment=dict(os.environ)
    environment.pop('LD_LIBRARY_PATH',None);environment.pop('LD_PRELOAD',None)
    os.execve(c['corobot_python'],[c['corobot_python'],str(entry)]+arguments,environment)


if __name__=='__main__':main()
