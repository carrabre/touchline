"""Detailed frame analysis for recordings the video scout cannot interpret.

Absolute source timestamps are attached to every frame. Unconfirmed incidents
remain review candidates; a second independent request must confirm a goal.
"""
import io,json,math,pathlib,subprocess
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

MODEL='us.anthropic.claude-sonnet-4-6'
VERSION='court-frames-v1'
SCOUT='''Inspect the actual soccer action in these ordered images, including indoor and small-sided games with portable goals. Each image is labeled with source-video seconds. First give a factual observation for EVERY image: ball visibility, kick, attack toward either goal, goalkeeper intervention, retrieval or reset. Then nominate attacking sequences toward a goal for independent review, even if the outcome is obscured. Small portable nets at floor level are goals; basketball hoops are not. Do not require celebrations, a scoreboard or formal kickoff in casual games. Return JSON only: {"observations":[{"time":source_seconds,"action":"visible action, not speculation"}],"events":[{"time":source_seconds,"kind":"goal|possible_goal","confidence":0.0,"evidence":"specific visible attack/shot/intervention and outcome; explain uncertainty"}]}. A save or miss can be a possible_goal candidate here; ordinary passing is not. Do not invent ball movement. Use only the provided source timestamps, not image numbers or a match clock.'''
REVIEW='''Independently check this soccer sequence, including small-sided/indoor games with portable nets, for an actual scored goal. Images are chronological and labeled with absolute SOURCE seconds. Inspect the attack, shot, outcome and subsequent play. First describe the visible action in a short observations list. A goal requires visible crossing into the goal, OR multiple specific corroborating observations of an obscured crossing (for example a shot into the goal followed by retrieval from inside the net and a restart). Formal celebration or a scoreboard is not required. A shot, save, rebound off the gym wall, player walking toward a goal, or play stopping alone is insufficient. Return JSON only: {"observations":[{"time":source_seconds,"action":"observed action and outcome"}],"worthwhile":true|false,"time":source_seconds,"kind":"goal|possible_goal","confidence":0.0,"evidence":"specific observed outcome and corroboration, at most 80 words"}. Use worthwhile false for ordinary play, a save or a miss. If a scoring incident occurred but the outcome is uncertain, use worthwhile true, possible_goal and confidence below 0.7. Never invent a goal or use a match clock. Evaluate the entire sequence.'''

def parse_response(response):
 text=''.join(c.get('text','') for c in response['output']['message']['content'])
 starts=[i for c in ('{','[') if (i:=text.find(c))>=0]
 if not starts:raise RuntimeError('Frame analysis returned no JSON; retrying.')
 data,_=json.JSONDecoder().raw_decode(text[min(starts):])
 if not isinstance(data,dict):raise RuntimeError('Frame analysis returned an invalid document.')
 return data,response.get('usage',{})

def windows(duration):
 for start in range(0,math.ceil(duration),20):
  yield start,min(24,duration-start)
  if start+24>=duration:break

def crop_bounds(scene):
 # Only a stationary indoor camera gets a fixed court crop. Outdoor/moving
 # footage retains the whole view. Invalid geometry must never hide a goal.
 if scene.get('stationary') is not True or scene.get('indoor') is not True:return (0,0,1,1)
 box=scene.get('playingArea')
 try:
  a,b,c,d=map(float,box)
  if not all(math.isfinite(v) and 0<=v<=1 for v in (a,b,c,d)) or c-a<.7 or d-b<.25:raise ValueError()
 except (TypeError,ValueError):return (0,0,1,1)
 return (max(0,a-.04),max(0,b-.04),min(1,c+.04),min(1,d+.04))

def extract_frames(source,directory,start,length,fps=20/24,limit=20):
 directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=True)
 for old in directory.glob('*.jpg'):old.unlink()
 subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-ss',str(start),'-i',str(source),'-t',str(length),'-vf',f'fps={fps}:start_time=0,scale=1536:-2','-frames:v',str(limit),'-q:v','3','-y',str(directory/'%03d.jpg')],capture_output=True,check=True,timeout=600)
 frames=[(round(start+(int(f.stem)-1)/fps,3),f) for f in sorted(directory.glob('*.jpg'))]
 frames=[(t,f) for t,f in frames if t<start+length]
 if not frames:raise RuntimeError('No frames decoded for detailed goal analysis.')
 return frames

def content_for_frames(frames,scene,prompt):
 content=[{'text':prompt}];a,b,c,d=crop_bounds(scene)
 for t,file in frames:
  with Image.open(file) as im:
   width,height=im.size;im=im.crop((int(a*width),int(b*height),int(c*width),int(d*height)));out=io.BytesIO();im.save(out,format='JPEG',quality=90)
  content.extend([{'text':f'Source video second {t:.3f}'},{'image':{'format':'jpeg','source':{'bytes':out.getvalue()}}}])
 return content

def classify(client,source,directory,duration):
 directory=pathlib.Path(directory);content=[{'text':'These images sample one soccer recording across its duration. Return JSON only: {"stationary":true|false,"indoor":true|false,"playingArea":[left,top,right,bottom],"evidence":"short description"}. Coordinates normalized 0..1. playingArea must bound the ENTIRE visible playing surface, BOTH small portable soccer goals at floor level, players and goalkeepers across ALL images, with margin. Exclude unnecessary ceiling/sky and foreground furniture. Basketball hoops are not soccer goals. Use stationary false if the camera pans/changes viewpoint materially and [0,0,1,1] when uncertain. Never crop away either goal.'}]
 for index,fraction in enumerate((.02,.25,.5,.75,.96)):
  start=min(duration*fraction,max(0,duration-1))
  frames=extract_frames(source,directory/f'scene-{index}',start,min(1,duration-start),fps=1,limit=1)
  content.extend(content_for_frames(frames,{},'Sample from this recording')[1:])
 return parse_response(client.converse(modelId=MODEL,messages=[{'role':'user','content':content}],inferenceConfig={'maxTokens':600,'temperature':0}))[0]

def scout(client,source,directory,start,length,scene):
 frames=extract_frames(source,directory,start,length)
 response=client.converse(modelId=MODEL,messages=[{'role':'user','content':content_for_frames(frames,scene,SCOUT)}],inferenceConfig={'maxTokens':3000,'temperature':0})
 data,usage=parse_response(response)
 if not isinstance(data.get('observations'),list) or not data['observations'] or not isinstance(data.get('events'),list):raise RuntimeError('Detailed scout omitted observations or events; retrying.')
 return {'start':start,'duration':length,'data':data,'usage':usage}

def events(result):
 out=[];start=result['start'];end=start+result['duration']
 for event in result['data']['events']:
  try:t=float(event['time']);confidence=float(event['confidence'])
  except (KeyError,TypeError,ValueError):continue
  if not (math.isfinite(t) and start<=t<end and .1<=confidence<=1):continue
  if event.get('kind') not in ('goal','possible_goal'):continue
  out.append({'time':round(t,1),'kind':event['kind'],'confidence':confidence,'evidence':str(event.get('evidence',''))[:700],'frameScout':True})
 return out

def review(client,source,directory,candidate,duration,scene):
 start=max(0,candidate-24);length=min(40,duration-start)
 frames=extract_frames(source,directory,start,length,fps=1,limit=40)
 # Bedrock allows up to twenty images per message. Keep full frame detail;
 # don't squeeze forty frames into one low-resolution contact sheet.
 messages=[{'role':'user','content':content_for_frames(frames[i:i+20],scene,REVIEW if i==0 else 'Continuation of the same chronological sequence. Return the requested observations and final assessment.')} for i in range(0,len(frames),20)]
 data,usage=parse_response(client.converse(modelId=MODEL,messages=messages,inferenceConfig={'maxTokens':2200,'temperature':0}))
 if not isinstance(data.get('worthwhile'),bool) or not isinstance(data.get('observations'),list) or not data['observations']:raise RuntimeError('Detailed goal review omitted its assessment; retrying.')
 if data['worthwhile']:
  try:
   if not (start<=float(data['time'])<start+length and 0<=float(data['confidence'])<=1) or data.get('kind') not in ('goal','possible_goal'):raise ValueError()
  except (KeyError,TypeError,ValueError):raise RuntimeError('Detailed goal review returned an invalid source timestamp or confidence.')
 return {'data':data,'usage':usage}

def parallel_results(items,work,workers=3):
 # Bounded batches: errors/restarts cannot leave hundreds of paid calls queued.
 items=list(items)
 with ThreadPoolExecutor(max_workers=workers) as pool:
  for start in range(0,len(items),workers):
   yield from pool.map(work,items[start:start+workers])

def retain_review_events(events,uncertain_limit=70):
 # Leave editor capacity for up to thirty confirmed/manually added goals.
 # Confirmed goals are never capped by the optional review-candidate limit.
 confirmed=[e for e in events if e.get('kind')!='possible_goal' or e.get('manual')]
 uncertain=sorted((e for e in events if e.get('kind')=='possible_goal' and not e.get('manual')),key=lambda e:(-e['confidence'],e['time']))
 return sorted(confirmed+uncertain[:uncertain_limit],key=lambda e:e['time'])
