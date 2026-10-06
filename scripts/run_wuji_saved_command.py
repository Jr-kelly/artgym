"""Reproduce an existing explicit native experiment command without editing results."""
import argparse,json,subprocess,sys
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('command',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Use a fresh output directory')
 c=json.loads(a.command.read_text());c[0]=sys.executable;c[c.index('--output')+1]=str(a.output);raise SystemExit(subprocess.call(c))
if __name__=='__main__':main()
