"""Ball-first goal discovery for fixed-camera indoor recordings.

Geometry proposes incidents, never scores goals. Independent native-detail image
review must see the ball inside a net; uncertain outcomes remain unchecked.
"""
import hashlib, math, pathlib, subprocess
import cv2
import numpy as np
cv2.setNumThreads(1)
import frame_goals

VERSION='net-ball-v3'
DETECTOR_VERSION='net-ball-v2'
MODEL='us.anthropic.claude-opus-5-5'
ASSET='worker-assets/models/rfdetr-nano-int8-6ae07760.onnx'
SHA256='6ae077607df147ff3024f046f2e974a8bfe55b4e776c08f5b719fd61617f5568'
FPS=6
PROMPT='''Independently verify actual goals in amateur indoor soccer. The first image is whole-court context: identify both goal openings and which way they face each other. Following images are chronological goal close-ups labeled in source seconds. Broad visible mesh may be SIDE/REAR net rather than the opening. Trace the cream/white soccer ball from court through the opening into the net. A ball clearly behind side-net/inside the goal is sufficient even if it rebounds out afterward. Celebration, scoreboard or formal kickoff are not required. A detector proposal is not proof. Reject heads, shoes, saves, wall rebounds, ball touching the outside net, and mere 2D overlap. If the ball is obscured, report uncertainty. Return JSON only: {"goal":true|false,"uncertain":true|false,"time":source_seconds_or_null,"confidence":0.0,"orientation":"goal opening and visible net surfaces","evidenceTimes":[source_seconds],"observations":[{"time":source_seconds,"ball":"actual visible position/path"}],"evidence":"specific direct visual evidence or rejection"}. Report only a NEW scored goal: a ball already resting inside at the start is not another goal. Maximum 12 observations. Never invent a ball or infer a goal solely from player movement.'''

def ensure_model(s3,bucket,root):
 path=pathlib.Path(root)/'models'/'rfdetr-nano.onnx';path.parent.mkdir(parents=True,exist_ok=True)
 valid=False
 if path.exists():
  with path.open('rb') as f:valid=hashlib.file_digest(f,'sha256').hexdigest()==SHA256
 if not valid:
  temp=path.with_suffix('.tmp');s3.download_file(bucket,ASSET,str(temp))
  with temp.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
  if actual!=SHA256:
   temp.unlink(missing_ok=True);raise RuntimeError('Ball detector asset failed SHA-256 verification.')
  temp.replace(path)
 return path

class BallDetector:
 def __init__(self,path,providers=None,threads=2):
  import onnxruntime as ort
  options=ort.SessionOptions();options.intra_op_num_threads=threads;options.inter_op_num_threads=1
  options.add_session_config_entry('session.intra_op.allow_spinning','0')
  self.session=ort.InferenceSession(str(path),options,providers=providers or ['CPUExecutionProvider'])
  self.input=self.session.get_inputs()[0].name
 def detect(self,bgr,threshold=.08):
  h,w=bgr.shape[:2]
  image=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB).astype(np.float32)/255
  image=cv2.resize(image,(384,384),interpolation=cv2.INTER_LINEAR)
  image=(image-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
  tensor=np.ascontiguousarray(image.transpose(2,0,1)[None],dtype=np.float32)
  outputs=dict(zip([x.name for x in self.session.get_outputs()],self.session.run(None,{self.input:tensor})))
  if not np.isfinite(outputs['dets']).all() or not np.isfinite(outputs['labels']).all():raise RuntimeError('Ball detector returned invalid numeric output.')
  boxes=outputs['dets'][0];scores=1/(1+np.exp(-np.clip(outputs['labels'][0,:,37],-80,80)))
  found=[]
  for i in np.argsort(scores)[::-1]:
   if scores[i]<threshold:break
   cx,cy,bw,bh=boxes[i];box=np.clip(np.array([cx-bw/2,cy-bh/2,cx+bw/2,cy+bh/2])*[w,h,w,h],0,[w,h,w,h]).tolist()
   if any(iou(box,r['box'])>.5 for r in found):continue
   found.append({'box':box,'confidence':float(scores[i])})
  return found

def iou(a,b):
 area=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
 return area/max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-area)

def propose_regions(median):
 # Conservative support: red/orange portable nets in the lower court. Other
 # cameras/nets keep the existing general scout; this heuristic never scores.
 h,w=median.shape[:2];hsv=cv2.cvtColor(median,cv2.COLOR_BGR2HSV)
 mask=cv2.inRange(hsv,np.array([0,130,100]),np.array([12,255,255]));mask[:int(.58*h)]=0
 mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
 _,_,stats,_=cv2.connectedComponentsWithStats(mask)
 posts=sorted([[int(x),int(y),int(a),int(b)] for x,y,a,b,area in stats[1:] if area>40 and b>h*.027 and b>2.5*a and a<w*.025])
 groups=[]
 for post in posts:
  if groups and post[0]-groups[-1][-1][0]-groups[-1][-1][2]<w*.065:groups[-1].append(post)
  else:groups.append([post])
 regions=[]
 for g in groups:
  x=min(a[0] for a in g);y=min(a[1] for a in g);r=max(a[0]+a[2] for a in g);b=max(a[1]+a[3] for a in g);height=max(b-y,h*.075)
  bounds=[max(0,int(x-height*.6)),max(0,int(y-height*.7)),min(w,int(r+height*1.8)),min(h,int(b+height*.65))]
  regions.append({'bounds':bounds,'goalHeight':height,'anchor':[x,y,r,b]})
 if len(regions)!=2 or (regions[1]['bounds'][0]-regions[0]['bounds'][2])<w*.2:return []
 return regions

def calibrate(client,source,directory,duration,scene):
 if scene.get('stationary') is not True or scene.get('indoor') is not True:return {'supported':False,'reason':'General camera analysis required.'}
 directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=True);frames=[]
 for i in range(16):
  t=duration*(.03+.94*i/15);fs=frame_goals.extract_frames(source,directory/f'sample-{i}',t,min(1,duration-t),fps=1,limit=1)
  frames.append(cv2.imread(str(fs[0][1])))
 median=np.median(np.stack(frames),axis=0).astype('uint8');h,w=median.shape[:2];regions=propose_regions(median)
 if not regions:return {'supported':False,'reason':'Both portable goals could not be localized safely.'}
 _,full=cv2.imencode('.jpg',median);content=[{'text':'Verify this fixed-camera soccer court and its two proposed goal crops. Return JSON only: {"bothGoals":true|false,"evidence":"where openings face"}. Each crop must contain an actual portable soccer goal at floor level. Temporary players or foreground bags may occlude the bottom: this does NOT invalidate an otherwise recognizable goal, and detection must still run on the visible region. Distinguish physical occlusion from a crop that cuts a goal off. Basketball hoops, door frames, wall padding and people are not goals. Say false only if either soccer goal is absent or cut off by the crop boundary, not because an object blocks part of a goal. Explain obstructions in evidence.'},{'image':{'format':'jpeg','source':{'bytes':full.tobytes()}}}]
 for region in regions:
  a,b,c,d=region['bounds'];_,crop=cv2.imencode('.jpg',median[b:d,a:c]);content.append({'image':{'format':'jpeg','source':{'bytes':crop.tobytes()}}})
 response=client.converse(modelId=MODEL,messages=[{'role':'user','content':content}],inferenceConfig={'maxTokens':1500})
 data,usage=frame_goals.parse_response(response)
 return {'supported':data.get('bothGoals') is True,'referenceSize':[w,h],'regions':regions,'evidence':str(data.get('evidence',''))[:700],'usage':usage,'fps':FPS}

def source_region(region,reference,width,height):
 sx=width/reference[0];sy=height/reference[1];a,b,c,d=region['bounds']
 return [int(a*sx),int(b*sy),min(width,int(c*sx)),min(height,int(d*sy))]

def net_volume(region,reference):
 x,y,r,b=region['anchor'];gh=region['goalHeight'];w,h=reference
 if r-x<=gh*.4:
  # One visible post: retain the net toward the court centre, plus margin.
  left=x-gh*(.25 if (x+r)/2<w/2 else 1.45)
  right=r+gh*(1.45 if (x+r)/2<w/2 else .25)
  top=y-gh*.4;bottom=b+gh*.4
 else:left=x-gh*.25;right=r+gh*.3;top=y-gh*.75;bottom=b+gh*.65
 return [max(0,left),max(0,top),min(w,right),min(h,bottom)]

def filter_sightings(rows,calibration,width,height):
 out=[];rw,rh=calibration['referenceSize']
 for row in rows:
  region=calibration['regions'][row['side']]
  if not region.get('anchor'):out.append(row);continue
  a,b,c,d=net_volume(region,(rw,rh));x1,y1,x2,y2=row['box']
  cx=(x1+x2)/2*rw/width;cy=(y1+y2)/2*rh/height
  gh=region['goalHeight']*height/rh
  if a<=cx<=c and b<=cy<=d and 2<=x2-x1<=gh*.25 and 2<=y2-y1<=gh*.25:out.append(row)
 return out

def scan_segment(detector,source,directory,start,length,calibration):
 directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=True);rows=[];frame_count=0
 cap=cv2.VideoCapture(str(source),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1]);width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));cap.release()
 # One native decode pass for both goals. fps precedes crop, no wide-view downscale.
 count=math.ceil(length*FPS)
 filters=['[0:v]fps='+str(FPS)+':start_time=0,split=2[a][b]']
 boxes=[source_region(r,calibration['referenceSize'],width,height) for r in calibration['regions']]
 for i,(a,b,c,d) in enumerate(boxes):filters.append(f'[{"a" if i==0 else "b"}]crop={c-a}:{d-b}:{a}:{b}[o{i}]')
 args=['ffmpeg','-nostdin','-v','error','-threads','1','-ss',str(start),'-t',str(length),'-i',str(source),'-filter_complex_threads','1','-filter_complex',';'.join(filters)]
 for i in range(2):args+=['-map',f'[o{i}]','-an','-frames:v',str(count),'-c:v','libx264','-threads','1','-preset','ultrafast','-crf','16','-y',str(directory/f'net-{i}.mp4')]
 subprocess.run(args,capture_output=True,check=True,timeout=600)
 for side,box in enumerate(boxes):
  cap=cv2.VideoCapture(str(directory/f'net-{side}.mp4'),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1]);index=0
  while True:
   ok,image=cap.read()
   if not ok:break
   t=round(start+index/FPS,4);index+=1
   if t>=start+length:continue
   goal_height=calibration['regions'][side]['goalHeight']*height/calibration['referenceSize'][1]
   for r in detector.detect(image):
    a,b,c,d=r['box'];bw=c-a;bh=d-b
    # Size relative to the net rejects distant heads and foreground feet. A
    # single fast ball detection can still propose a goal; no dwell minimum.
    if not (2<=bw<=goal_height*.32 and 2<=bh<=goal_height*.32 and .45<=bw/max(bh,1)<=2.2):continue
    rows.append({'side':side,'t':t,'box':[a+box[0],b+box[1],c+box[0],d+box[1]],'confidence':r['confidence']})
  cap.release()
  if index<max(1,math.floor(length*FPS)-1):raise RuntimeError('Incomplete native goal scan; segment must retry.')
  frame_count+=index
 return {'start':start,'length':length,'rows':filter_sightings(rows,calibration,width,height),'frames':frame_count,'sourceSize':[width,height],'modelSHA256':SHA256,'version':DETECTOR_VERSION,'fps':FPS}

def candidates(rows,gap=4):
 groups=[]
 for side in sorted(set(r['side'] for r in rows)):
  current=[]
  for r in sorted((r for r in rows if r['side']==side),key=lambda r:r['t']):
   if current and r['t']-current[-1]['t']>gap:groups.append(current);current=[]
   current.append(r)
  if current:groups.append(current)
 out=[]
 for g in groups:
  # Bound review calls without discarding long incidents or imposing a goal cap.
  buckets={}
  for r in g:buckets.setdefault(int((r['t']-g[0]['t'])/8),[]).append(r)
  for chunk in buckets.values():out.append({'side':chunk[0]['side'],'time':chunk[0]['t'],'lastSeen':chunk[-1]['t'],'peakTime':max(chunk,key=lambda r:r['confidence'])['t'],'detections':len(chunk),'episode':f"{g[0]['side']}:{g[0]['t']:.3f}"})
 return sorted(out,key=lambda e:e['time'])

def review_region(region,reference,second_view=False):
 if not region.get('anchor'):return region
 x,y,r,b=region['anchor'];gh=region['goalHeight'];rw,rh=reference
 if second_view and r-x>gh*.4:
  return {**region,'bounds':[max(0,int(x-gh*.25)),max(0,int(y-gh*.75)),min(rw,int(r+gh*.3)),min(rh,int(b+gh*.65))]}
 if not second_view and (x+r)/2>rw/2:
  # The right goal faces LEFT. Put context on the court/shot-approach side,
  # rather than spending image detail on the wall behind the net.
  return {**region,'bounds':[max(0,int(x-gh*1.8)),max(0,int(y-gh*.7)),min(rw,int(r+gh*.6)),min(rh,int(b+gh*.65))]}
 return region

def verify(client,source,directory,candidate,duration,calibration,model_id=MODEL,second_view=False,tie_break=False):
 directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=True)
 # Keep the full court for orientation, then dense close-ups plus retrieval.
 cap=cv2.VideoCapture(str(source),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1]);width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 t=float(candidate['peakTime']);start=max(0,float(candidate['time'])-2);end=min(duration,float(candidate['lastSeen'])+4)
 # Split long episodes by caller; do not silently sample away a second goal.
 if end-start>24:raise RuntimeError('Net episode exceeds dense review window.')
 region=review_region(calibration['regions'][candidate['side']],calibration['referenceSize'],second_view)
 a,b,c,d=source_region(region,calibration['referenceSize'],width,height)
 # Dense ordered frames throughout, including fast net contact and rebounds.
 fps=5 if second_view else 8;offset=1/30 if tie_break else .0625 if second_view else 0
 if tie_break:
  dense_start=max(start,t-2);dense_end=min(end,t+2)
  times=sorted(set([round(start+offset+i/2,3) for i in range(math.ceil((end-start-offset)*2))]+[round(dense_start+offset+i/15,3) for i in range(math.ceil((dense_end-dense_start-offset)*15))]))
 elif second_view:
  times=[round(start+offset+i/fps,3) for i in range(math.ceil((end-start-offset)*fps))]
 else:
  # Review the complete incident at 2fps, with dense 8fps coverage around the
  # detector's strongest ball sighting. This preserves temporal context without
  # sending scores of near-identical frames to the model.
  dense_start=max(start,t-2);dense_end=min(end,t+2)
  times=sorted(set([round(start+i/2,3) for i in range(math.ceil((end-start)*2))]+[round(dense_start+i/8,3) for i in range(math.ceil((dense_end-dense_start)*8))]))
 cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,full=cap.read()
 if not ok:raise RuntimeError('Cannot decode court context.')
 full=cv2.resize(full,(1536,int(height*1536/width)));_,data=cv2.imencode('.jpg',full)
 content=[{'text':PROMPT},{'text':f'Whole-court context at source second {t:.3f}; not a scoring label.'},{'image':{'format':'jpeg','source':{'bytes':data.tobytes()}}}]
 cap.release()
 # Decode the native crop once at the densest grid, then select the labeled
 # frames for the requested overview/dense sampling grid.
 for old in directory.glob('*.jpg'):old.unlink()
 actual_start=start+offset;decode_fps=15 if tie_break else 5 if second_view else 8;scale=1280 if tie_break else 900
 subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-ss',str(actual_start),'-i',str(source),'-t',str(end-actual_start),'-filter_threads','1','-vf',f'crop={c-a}:{d-b}:{a}:{b},fps={decode_fps}:start_time=0,scale={scale}:-2','-threads','1','-q:v','2','-y',str(directory/'%04d.jpg')],capture_output=True,check=True,timeout=600)
 files=sorted(directory.glob('*.jpg'));expected=math.ceil((end-actual_start)*decode_fps)
 if len(files)<max(1,expected-1):raise RuntimeError('Incomplete net verification decode.')
 for index in sorted(set(round((sec-actual_start)*decode_fps) for sec in times)):
  if index>=len(files):continue
  actual=actual_start+index/decode_fps
  content.extend([{'text':f'Source second {actual:.3f}'},{'image':{'format':'jpeg','source':{'bytes':files[index].read_bytes()}}}])
 # At most twenty images per Bedrock message; split on image-pair boundaries.
 messages=[];part=content[:3];images=1
 for i in range(3,len(content),2):
  if images==20:messages.append({'role':'user','content':part});part=[{'text':'Chronological continuation; return final assessment after all frames.'}];images=0
  part+=content[i:i+2];images+=1
 if images:messages.append({'role':'user','content':part})
 response=client.converse(modelId=model_id,messages=messages,inferenceConfig={'maxTokens':10000},additionalModelRequestFields={'thinking':{'type':'adaptive'},'output_config':{'effort':'medium'}})
 data,usage=frame_goals.parse_response(response)
 if not isinstance(data.get('goal'),bool) or not isinstance(data.get('uncertain'),bool) or not isinstance(data.get('observations'),list) or not data['observations']:raise RuntimeError('Invalid net verification response.')
 try:
  confidence=float(data['confidence'])
  if not math.isfinite(confidence) or not 0<=confidence<=1 or not isinstance(data.get('evidence'),str) or not data['evidence'].strip():raise ValueError()
 except (KeyError,ValueError,TypeError):raise RuntimeError('Invalid net verification confidence or evidence.')
 if data['goal']:
  try:
   if data['uncertain'] or not start<=float(data['time'])<end or not .6<=float(data['confidence'])<=1 or not isinstance(data.get('evidenceTimes'),list) or not data['evidenceTimes'] or not all(start<=float(e)<end for e in data['evidenceTimes']):data['goal']=False;data['uncertain']=True
  except (ValueError,TypeError):raise RuntimeError('Invalid ball-in-net evidence timestamps.')
 return {'data':data,'usage':usage,'window':[start,end],'candidate':candidate,'model':model_id,'secondView':second_view,'tieBreak':tie_break}


def agreement(primary,secondary):
 """Two independent requests must see a new goal in the same source interval."""
 for result in (primary,secondary):
  d=result['data']
  try:
   if d.get('goal') is not True or d.get('uncertain') is not False or not .6<=float(d['confidence'])<=1 or not math.isfinite(float(d['time'])) or not d.get('evidenceTimes'):return False
  except (TypeError,ValueError,KeyError):return False
 return abs(float(primary['data']['time'])-float(secondary['data']['time']))<=4


def consensus(results):
 """Uncertainty is not a negative vote; require two direct, coherent positives."""
 for i,first in enumerate(results):
  for second in results[i+1:]:
   if agreement(first,second):return sorted([first,second],key=lambda r:float(r['data']['time']))
 return None
