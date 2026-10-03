"""Decode every frame of delivered independent media; not human video review."""
import pathlib,json,hashlib,concurrent.futures,cv2,numpy as np,datetime
from scripts.record_wuji_robust_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003';base=R/'runs/robust-knife-family-20261003';files=sorted(f for folder in (base/'checks').glob('independent-*') for f in folder.glob('*.mp4'));files.append(base/'delivery/continuous-demo-success-and-failure-v2.mp4');assert len(files)==97;record('complete_delivered_video_decode_audit_started',config={'files':len(files),'threads':4},next='Decode actualallframes; nohumanframebyframe claim, taskcriteria/outcomes unchanged')
def audit(path):
 cap=cv2.VideoCapture(str(path));expected=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=float(cap.get(cv2.CAP_PROP_FPS));n=0;dark=0;still=0;longest=0;previous=None;low=256;high=-1;run=0
 while True:
  ok,frame=cap.read()
  if not ok:break
  n+=1;gray=cv2.cvtColor(cv2.resize(frame,(64,36)),cv2.COLOR_BGR2GRAY);mean=float(gray.mean());low=min(low,mean);high=max(high,mean);dark+=int(mean<1)
  identical=previous is not None and np.array_equal(gray,previous)
  if identical:still+=1;run+=1;longest=max(longest,run)
  else:run=0
  previous=gray
 cap.release();assert n==expected and expected in [1080,2160],(path,n,expected);assert dark==0,(path,dark)
 return {'path':str(path.relative_to(R)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fps':fps,'frames_decoded':n,'metadata_frame_count':expected,'duration_seconds':n/fps,'black_frames_by_mean_lt1':dark,'mean_luminance_min_max':[low,high],'identical_64x36_gray_successive_frame_pairs':still,'longest_identical_thumbnail_frame_run':longest,'scope':'Automatedfullframe decode/quality audit, not human frame-byframe motion review or extra physicaltrial.'}
with concurrent.futures.ThreadPoolExecutor(4) as pool:rows=list(pool.map(audit,files))
j={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':len(rows),'frames_decoded':sum(r['frames_decoded'] for r in rows),'total_duration_seconds':sum(r['duration_seconds'] for r in rows),'videos':rows,'scope':'Everydeliveredprimary independent video plusderived2160frameV2 montage decoded once; no changing taskoutcomes/media selection. Sampledvisualreview remains separate.'};p=D/'delivered-video-full-decode-audit.json';p.write_text(json.dumps(j,indent=2));record('complete_delivered_video_decode_audit_completed',evidence=str(p.relative_to(R)),config={'files':j['files'],'frames':j['frames_decoded']},next='Finishdownloadrestore andpublishoriginalactualmedia');print({k:v for k,v in j.items() if k!='videos'})
