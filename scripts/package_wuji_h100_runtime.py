"""Preserve H100 rendering failures, process-lifetime library fix and both-host gates."""
from pathlib import Path
import hashlib,json,shutil,zipfile

def main():
 r=Path(__file__).resolve().parents[1];d=r/'runs/wuji-goal/diagnostics';out=d/'release-h100-rendering-runtime-20260923T1950-v2';out.mkdir(exist_ok=False);prefix='wuji-h100-rendering-both-hosts-20260923'
 names=['rgb-egl-four-cleanup-device1-1749-v7','rgb-egl-preload-loader-1753-v8','rgb-egl-retain-driver-1755-v9','rgb-egl-eight-retain-driver-1758-v10'];runs={name:json.loads((d/name/'status.json').read_text()) for name in names}
 audits={key:json.loads((d/name).read_text()) for key,name in [('four','rgb-egl-four-all-gates-rescored-1810-v1.json'),('eight','rgb-egl-eight-all-gates-rescored-1945-v1.json')]}
 assert all(a['status']=='verified_runtime_gates' and a['physics_transitions']==53400 for a in audits.values())
 assert all(runs[name]['status']=='completed' and all(x['returncode']==0 for x in runs[name]['stages']) for name in names[2:])
 assert all(runs[name]['status']=='failed' for name in names[:2])
 (out/(prefix+'-all-gate-audits.json')).write_text(json.dumps(audits,indent=2)+'\n')
 (out/(prefix+'-README.txt')).write_text('''H100 rendering runtime validation: four-card and eight-card development hosts

Both hosts completed RGB3, masked3 and RGB83 gates with normal exit0. Each
host has53400 physical transitions independently rescored. Success counts on
these old baseline-model development states are3/3,1/3,76/83 respectively.
These are runtime/capacity checks, not independent task or hardware results.
The completed primary independent evaluation remained on local4090 throughout.
Local83 baseline had77 successes; H100 gates had76. Do not silently substitute
one numerical evaluation protocol for another when reporting reliability.

The NVIDIA kernel was560.35.03 while container graphics entries were565.77
zero-byte placeholders. Matching official560.35.03 components were extracted
into an isolated user directory, with no host driver installation. The exact
extraction manifest, component hashes and EGL ICD are included as provenance.
The binaries themselves are not part of this evidence archive; use the source
package identified by the included package-provenance JSON (URL, deb hash,
size and extraction command), and reproduce the component hashes. The Vulkan
loader came from local Ubuntu libvulkan1:amd64 version1.3.204.1-2; its exact
path, size and matching SHA256 are separately recorded in that provenance.

Set LD_LIBRARY_PATH to the isolated usr/lib/x86_64-linux-gnu directory before
process startup. Use its nvidia_egl_icd.json in VK_ICD_FILENAMES. LD_PRELOAD
must retain the matched libvulkan.so.1,libEGL_nvidia.so.0,
libnvidia-eglcore.so.560.35.03,libnvidia-glvkspirv.so.560.35.03 and
libnvidia-rtcore.so.560.35.03 for process lifetime. Exact absolute paths and
hashes are in each successful spec. The launcher itself also needs this
LD_LIBRARY_PATH when it inherits LD_PRELOAD.

Unmask CUDA_VISIBLE_DEVICES and explicitly use the same physical compute and
graphics ordinal, including torch.cuda.set_device. Lease only the designated
physical GPU. Retain other training/checkpoint workers. Cameras are explicitly
destroyed before the existing simulator teardown, which runs exactly once.

Negative controls are preserved: v7 explicit camera/simulator cleanup and v8
Vulkan-loader-only preload both finished their rollout but exited-11 during
native shutdown. Their physical/prediction arrays were checked identical.
Changing only loader or ignoring the exit signal did not solve the problem.
Full driver-component lifetime retention in v9/v10 yielded ordinary exit0.
No os._exit workaround or hidden successful-process reclassification was used.

The ZIP includes all four runs and their logs/traces/diagnostic images,
independent audits, source pin archive, extraction/ICD provenance, and this
packaging source. Assets are named; all camera images contain no text.
''')
 source=runs[names[2]]['spec']['source'];archive=out/(prefix+'-complete-evidence.zip');added=set()
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  def add(p,name):
   assert p.is_file() and name not in added,(p,name);z.write(p,name);added.add(name)
  for name in names:
   for p in sorted((d/name).rglob('*')):
    if p.is_file() and not p.is_symlink():add(p,'runs/'+name+'/'+str(p.relative_to(d/name)))
  for key in ['archive','manifest']:
   p=r/source[key];assert hashlib.sha256(p.read_bytes()).hexdigest()==source[key+'_sha256'];add(p,'source/'+p.name)
  for p in [d/'rgb-egl-v7-v8-trace-equality-1755.json',d/'h100-vulkan-isolated-1713-v2/manifest.json',d/'h100-vulkan-isolated-1713-v2/nvidia_egl_icd.json',d/'h100-driver-package-provenance-1950.json',Path(__file__)]:add(p,'provenance/'+p.name)
  for p in out.glob('*.json'):add(p,p.name)
  add(out/(prefix+'-README.txt'),'README.txt')
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 files=sorted(p for p in out.iterdir() if p.is_file());m={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files};(out/(prefix+'-manifest.json')).write_text(json.dumps(dict(assets=m,source=source),indent=2)+'\n')
 (out/'package-status.json').write_text(json.dumps(dict(status='completed',files=len(added),archive_sha256=m[archive.name]['sha256'],bytes=archive.stat().st_size),indent=2)+'\n');print(out)
if __name__=='__main__':main()
