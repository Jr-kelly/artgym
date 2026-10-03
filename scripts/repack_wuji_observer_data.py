"""Losslessly reorder overlapping history windows for compact recovery delivery.

The unpacker restores the original sample order, field order, dtype and array
bytes. No labels or physical samples are removed or quantized.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def array_sha(v):return hashlib.sha256(v.tobytes(order='C')).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['pack','unpack'],required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--envs',type=int,default=512);a=p.parse_args();assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True)
 with np.load(a.input) as z:
  if a.mode=='pack':
   fields=z.files;assert set(fields)=={'packets','features','labels','groups','times'};n=len(z['times']);assert n%a.envs==0
   order=np.arange(n).reshape(-1,a.envs).T.reshape(-1);original={k:z[k] for k in fields};values={k:original[k][order] for k in fields};values['row_order']=order
   receipt=dict(original_sha256=sha(a.input),original_bytes=a.input.stat().st_size,fields=fields,envs=a.envs,array_sha256={k:array_sha(v) for k,v in original.items()},scope='Lossless environment-major compression of overlapping50frame windows; unpack before originalheadtraining to restore originalorder. No sample selection orprecision change.')
  else:
   receipt=json.loads(a.input.with_suffix(a.input.suffix+'.json').read_text());fields=receipt['fields'];inverse=np.argsort(z['row_order']);values={k:z[k][inverse] for k in fields}
   assert all(array_sha(values[k])==receipt['array_sha256'][k] for k in fields)
 np.savez_compressed(a.output,**values);receipt['output_sha256']=sha(a.output);receipt['output_bytes']=a.output.stat().st_size
 if a.mode=='unpack':receipt['original_container_sha256_matched']=receipt['output_sha256']==receipt['original_sha256']
 a.output.with_suffix(a.output.suffix+'.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if __name__=='__main__':main()
