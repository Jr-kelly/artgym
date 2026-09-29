"""Read-only five-second all-device samples, bounded by the goal deadline."""
import datetime,json,time,subprocess,os
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/'runs/unified-policy-20260930'
end=datetime.datetime.fromisoformat('2026-09-30T07:56:50+00:00').timestamp()
(B/'resource-monitor.json').write_text(json.dumps(dict(pid=os.getpid(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),deadline_utc='2026-09-30T07:56:50Z',interval_seconds=5))+'\n')
while time.time()<end:
 started=time.monotonic()
 try:
  output=subprocess.check_output(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used','--format=csv,noheader'],text=True,timeout=10)
  row=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),gpus=output)
 except (subprocess.SubprocessError,OSError) as e:row=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),error=str(e))
 with (B/'machine-gpu-history.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 time.sleep(max(.1,5-(time.monotonic()-started)))
