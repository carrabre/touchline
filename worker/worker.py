"""Single-flight durable media worker. No inbound network ports; EC2 IAM role only."""
import os,json,time,uuid,subprocess,math,pathlib,shutil,logging,tempfile
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from soundtracks import select_music,mix_music
from PIL import Image,ImageDraw,ImageFont
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
REGION=os.getenv('AWS_DEFAULT_REGION','us-east-1');BUCKET=os.environ['MEDIA_BUCKET'];TABLE=os.environ['MATCH_TABLE'];ROOT=pathlib.Path(os.getenv('WORK_DIR','/data'))
CONFIG=Config(retries={'max_attempts':5,'mode':'standard'},read_timeout=300,connect_timeout=30)
s3=boto3.client('s3',region_name=REGION,config=CONFIG);ddb=boto3.client('dynamodb',region_name=REGION,config=CONFIG);model=boto3.client('bedrock-runtime',region_name=REGION,config=CONFIG)
LITE='us.amazon.nova-2-lite-v1:0';PRO=LITE;VERSION='touchline-goals-2';ROOT.mkdir(parents=True,exist_ok=True)
class InvalidVideo(Exception):pass
class LostLease(Exception):pass
def run(args,timeout=900):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(p.stderr[-1600:])
 return p.stdout

def probe(path):
 try:d=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],90))
 except Exception as e:raise InvalidVideo('This file could not be decoded. Export it as a standard MP4 and try again.') from e
 v=next((x for x in d['streams'] if x['codec_type']=='video'),None)
 if not v:raise InvalidVideo('This file contains no video stream.')
 duration=float(d['format'].get('duration') or v.get('duration') or 0)
 if not 1<=duration<=7200.15:raise InvalidVideo(f'Video duration is {duration:.1f} seconds. Supported range: 1 second to 2 hours.')
 if v['width']>7680 or v['height']>4320:raise InvalidVideo('Maximum supported source resolution is 8K. Export a smaller MP4.')
 return d,duration,v

def save(m,lease,stage=None):
 if stage:m['status']=stage
 ddb.update_item(TableName=TABLE,Key={'id':{'S':m['id']}},UpdateExpression='SET doc=:d, stage=:s, lease=:next, updated=:u',ConditionExpression='lease=:old AND revision=:r',ExpressionAttributeValues={':d':{'S':json.dumps(m)},':s':{'S':m['status']},':next':{'N':str(lease)},':old':{'N':str(lease)},':r':{'N':str(m['revision'])},':u':{'N':str(int(time.time()*1000))}})

def heartbeat(m,lease,stage=None):
 # Token is an opaque timestamp+fraction used only for compare-and-swap, with a 30 minute TTL.
 fresh=time.time()+1800
 try:
  ddb.update_item(TableName=TABLE,Key={'id':{'S':m['id']}},UpdateExpression='SET doc=:d, stage=:s, lease=:next, updated=:u',ConditionExpression='lease=:old AND revision=:r',ExpressionAttributeValues={':d':{'S':json.dumps(m)},':s':{'S':stage or m['status']},':next':{'N':str(fresh)},':old':{'N':str(lease)},':r':{'N':str(m['revision'])},':u':{'N':str(int(time.time()*1000))}})
 except ClientError as e:raise LostLease() from e
 m['status']=stage or m['status'];return fresh

def checkpoint(key,doc):s3.put_object(Bucket=BUCKET,Key=key,Body=json.dumps(doc).encode(),ContentType='application/json')
def load_checkpoint(key):
 try:return json.loads(s3.get_object(Bucket=BUCKET,Key=key)['Body'].read())
 except ClientError as e:
  if e.response['Error']['Code'] in ['NoSuchKey','404']:return None
  raise

def vision(path,prompt,model_id,mode="scout"):
 result=model.converse(modelId=model_id,messages=[{'role':'user','content':[{'video':{'format':'mp4','source':{'bytes':path.read_bytes()}}},{'text':prompt}]}],inferenceConfig={'maxTokens':1200,'temperature':0.2})
 text=''.join(x.get('text','') for x in result['output']['message']['content'])
 starts=[i for token in ('{','[') if (i:=text.find(token))>=0]
 if not starts:raise RuntimeError('Video model returned no structured result; retrying this segment.')
 data,_=json.JSONDecoder().raw_decode(text[min(starts):])
 if mode=='scout' and isinstance(data,list):data={'events':data}
 if not isinstance(data,dict):raise RuntimeError('Invalid video response; segment will retry.')
 if mode=='scout' and isinstance(data.get('goals'),list):
  data={'events':[{'time':e.get('time'),'kind':'goal' if e.get('confirmed') is True else 'possible_goal','confidence':.9 if e.get('confirmed') is True else .55,'evidence':e.get('evidence','')} for e in data['goals'] if isinstance(e,dict)]}
 if mode=='scout' and not isinstance(data.get('events'),list):raise RuntimeError('Invalid scout response; segment will retry.')
 if mode=='review' and not isinstance(data.get('worthwhile'),bool):raise RuntimeError('Invalid review response; candidate will retry.')
 if mode=='review' and data['worthwhile']:
  try:
   if not math.isfinite(float(data['time'])) or float(data['time'])<0 or not 0<=float(data['confidence'])<=1 or data.get('kind') not in ['goal','possible_goal']:raise ValueError()
  except (KeyError,TypeError,ValueError):raise RuntimeError('Review omitted a valid goal timestamp or confidence; candidate will retry.')

 return data,result.get('usage',{})

SCOUT='''Find actual soccer GOALS that occur during this video. Look through its entire duration. A prior score on the scoreboard is not a new goal. A score change alone is insufficient: locate the attacking sequence, shot and ball entering the net, then corroborating celebration or restart. Do not count saves, misses, routine passing, old scores or replays as a new goal. If the outcome is uncertain, mark confirmed false and explain. Return JSON only: {"goals":[{"time":elapsed_clip_seconds,"confirmed":true|false,"evidence":description_under_40_words}]}. Never use the scoreboard clock for time. Empty goals is valid. Be precise and do not invent events.'''
DEEP='''Independently inspect this soccer sequence for an actual GOAL. The video is at half speed: use elapsed seconds in this slowed video, never the scoreboard clock. Require observable ball entering the net and corroborating celebration, referee signal or score change. A score already visible at the start is not a new goal. Reject saves, misses, replays and routine play. No audio is supplied. Return JSON only: {"worthwhile":true|false,"time":elapsed_seconds_in_this_slowed_clip,"kind":"goal|possible_goal","confidence":0.0,"evidence":"Observed action and outcome, at most 40 words"}. Use worthwhile false if no goal is seen. Ambiguous outcomes must be possible_goal with confidence below 0.7.'''

def extract(source,out,start,duration,slow=False):
 vf='scale=768:-2,fps=2'+(',setpts=2*PTS' if slow else '')
 run(['ffmpeg','-nostdin','-v','error','-threads','2','-ss',str(start),'-i',str(source),'-t',str(duration*(2 if slow else 1)),'-an','-vf',vf,'-c:v','libx264','-threads','2','-preset','veryfast','-crf','28','-movflags','+faststart','-y',str(out)],600)

def dedup(events):
 out=[]
 for e in sorted(events,key=lambda e:e['time']):
  if out and abs(e['time']-out[-1]['time'])<12:
   if e['confidence']>out[-1]['confidence']:out[-1]=e
  else:out.append(e)
 return out

def review_candidates(events,other_limit=40):
 ordered=sorted(events,key=lambda e:(0 if e['kind'] in ['goal','possible_goal'] else 1,-e['confidence']))
 goals=[e for e in ordered if e['kind'] in ['goal','possible_goal']]
 others=[e for e in ordered if e['kind'] not in ['goal','possible_goal']]
 return goals+others[:other_limit]

def choose(events,target):
 selected=[];total=0
 for e in sorted((x for x in events if x['included']),key=lambda x:(0 if x.get('manual') else 1,{'goal':0,'save':1,'close_chance':2,'impressive_play':3,'possible_goal':4}.get(x['kind'],3),-x['confidence'])):
  length=e['end']-e['start']
  if e['kind']=='goal' or total+length<=target or not selected:selected.append(dict(e));total+=length
 selected.sort(key=lambda e:e['start']);merged=[]
 for e in selected:
  if merged and e['start']<=merged[-1]['end']+.5:merged[-1]['end']=max(merged[-1]['end'],e['end'])
  else:merged.append(e)
 return merged

def render(source,directory,m,clips):
 info,duration,v=probe(source);audio=any(x['codec_type']=='audio' for x in info['streams']);clipfiles=[];offset=0
 for i,e in enumerate(clips):
  out=directory/f'clip-{i:03}.mp4';length=e['end']-e['start']
  sar=v.get('sample_aspect_ratio','1:1');ratio=1
  try:aa,bb=map(float,sar.split(':'));ratio=aa/bb if bb else 1
  except (ValueError,TypeError):pass
  width=int(v['width']*ratio)//2*2;height=v['height']//2*2
  fontpath=next((x for x in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/System/Library/Fonts/Supplemental/Arial.ttf'] if pathlib.Path(x).exists()),None)
  def overlay(path,text,y,center=False):
   image=Image.new('RGBA',(width,height),(0,0,0,0));draw=ImageDraw.Draw(image)
   if text:
    fontsize=max(12,min(int(height/30),int(width/(max(len(text),1)*.65+2))))
    font=ImageFont.truetype(fontpath,fontsize) if fontpath else ImageFont.load_default(size=fontsize)
    bounds=draw.textbbox((0,0),text,font=font);tw=bounds[2]-bounds[0];th=bounds[3]-bounds[1]
    x=(width-tw)//2 if center else int(width*.03);padding=max(6,int(height*.015))
    draw.rounded_rectangle((x-padding,y-padding,x+tw+padding,y+th+padding),radius=4,fill=(0,0,0,150));draw.text((x,y-bounds[1]),text,font=font,fill='white')
   image.save(path)
  titlepng=directory/'title.png';labelpng=directory/'label.png'
  overlay(titlepng,m['title'][:100] if i==0 else '',int(height*.08),True)
  label=f"{int(e['time']//60)}:{int(e['time']%60):02d} {e['kind'].replace('_',' ').title()}" if m['labels'] else ''
  overlay(labelpng,label,int(height*.89))
  vf="[0:v]scale=trunc(iw*sar/2)*2:trunc(ih/2)*2,setsar=1,format=yuv420p[base];[base][1:v]overlay=0:0:enable='lt(t,3)'[title];[title][2:v]overlay=0:0:enable='lt(t,4)'[v]"
  args=['ffmpeg','-nostdin','-v','error','-threads','2','-ss',str(e['start']),'-i',str(source),'-i',str(titlepng),'-i',str(labelpng)]
  if not audio:args+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
  args+=['-t',str(length),'-filter_complex',vf,'-map','[v]','-map','0:a:0' if audio else '3:a:0','-c:v','libx264','-threads','2','-preset','fast','-crf','20','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-avoid_negative_ts','make_zero','-y',str(out)]
  run(args,900);clipfiles.append(out);offset+=length
 playlist=directory/'clips.txt';playlist.write_text(''.join(f"file '{x}'\n" for x in clipfiles));cut=directory/'cut.mp4'
 run(['ffmpeg','-nostdin','-v','error','-f','concat','-safe','0','-i',str(playlist),'-c','copy','-y',str(cut)],300)
 final=mix_music(cut,directory,m,offset,run)
 outinfo,outduration,_=probe(final)
 if abs(outduration-offset)>1:raise RuntimeError('Rendered duration failed validation.')
 return final,outduration,clips

def process(item,lease):
 m=json.loads(item['doc']['S']);m['status']='ingestion';directory=ROOT/m['id'];directory.mkdir(exist_ok=True);source=directory/'source';started=time.time();metrics=m.get('metrics',{});metrics.setdefault('firstStarted',started);metrics['visionVersion']=VERSION
 try:
  if not source.exists():
   if shutil.disk_usage(ROOT).free < m['size']*1.15+2*1024**3:raise RuntimeError('The media worker has insufficient temporary disk space. Saved footage is safe; retry after storage is available.')
   if m.get('recording'):
    with source.open('wb') as w:
     for n in range(1,m['parts']+1):
      body=s3.get_object(Bucket=BUCKET,Key=f"{m['key']}/segments/{n:05d}")['Body']
      for chunk in body.iter_chunks(1024*1024):w.write(chunk)
    # WebM recordings often lack duration metadata. Remux to a seekable MP4 before analysis.
    normalized=directory/('normalized.mp4' if m['mime']=='video/mp4' else 'normalized.webm')
    run(['ffmpeg','-nostdin','-v','error','-threads','2','-i',str(source),'-map','0:v:0','-map','0:a?','-c','copy','-y',str(normalized)],18000)
    source.unlink();normalized.rename(source);s3.upload_file(str(source),BUCKET,m['key'],ExtraArgs={'ContentType':m['mime']})
   else:s3.download_file(BUCKET,m['key'],str(directory/'download.tmp'));(directory/'download.tmp').rename(source)
  info,duration,v=probe(source);m['duration']=duration;m['metrics']=metrics
  if not m.get('analysisComplete'):
   all_events=[];usage={'inputTokens':0,'outputTokens':0};coverage=0
   for index,start in enumerate(range(0,math.ceil(duration),170)):
    actual=min(180,duration-start);ck=f"analysis/{m['id']}/{VERSION}/scout-{index}.json";result=load_checkpoint(ck)
    m['note']=f'Reviewing {start//60}:{start%60:02d} to {int((start+actual)//60)}:{int((start+actual)%60):02d}';m['analyzed']=coverage;lease=heartbeat(m,lease,'analysis')
    if not result:
     clip=directory/'analysis.mp4';extract(source,clip,start,actual);data,tokens=vision(clip,SCOUT,LITE);result={'start':start,'duration':actual,'data':data,'usage':tokens};checkpoint(ck,result)
    for k in usage:usage[k]+=result['usage'].get(k,0)
    if not isinstance(result['data'].get('events'),list):raise RuntimeError('Analysis schema invalid.')
    for e in result['data']['events']:
     try:t=float(e['time']);c=float(e['confidence'])
     except (KeyError,TypeError,ValueError):continue
     if not (0<=t<actual and .3<=c<=1):continue
     if e.get('kind') not in ['goal','save','close_chance','impressive_play','possible_goal']:continue
     all_events.append({'time':round(start+t,1),'kind':e['kind'],'confidence':c,'evidence':str(e.get('evidence',''))[:700]})
    coverage=max(coverage,min(duration,start+actual));m['analyzed']=coverage;lease=heartbeat(m,lease,'analysis')
   candidates=dedup(all_events);events=[]
   # Every goal candidate gets an independent review; only optional action is capped.
   candidates=review_candidates(candidates)
   for idx,e in enumerate(candidates):
    start=max(0,e['time']-20);length=min(64,duration-start);ck=f"analysis/{m['id']}/{VERSION}/deep-{int(e['time']*10)}.json";result=load_checkpoint(ck);m['note']=f'Checking candidate {idx+1} of {len(candidates)} at {int(e["time"]//60)}:{int(e["time"]%60):02d}';lease=heartbeat(m,lease,'analysis')
    if not result:
     clip=directory/'analysis.mp4';extract(source,clip,start,length,True);data,tokens=vision(clip,DEEP,PRO,mode="review")
     if data['worthwhile'] and not 0<=float(data['time'])<=length*2:raise RuntimeError('Goal review timestamp is outside its video; retrying candidate.')
     result={'data':data,'usage':tokens};checkpoint(ck,result)
    for k in usage:usage[k]+=result['usage'].get(k,0)
    data=result['data']
    if not data.get('worthwhile'):continue
    t=start+max(0,min(length,float(data.get('time',24))/2));confidence=max(0,min(1,float(data.get('confidence',.5))));kind=data.get('kind','close_chance')
    if kind not in ['goal','save','close_chance','impressive_play','possible_goal']:continue
    if kind=='goal' and confidence<.85:kind='possible_goal';confidence=min(confidence,.65)
    event={'id':uuid.uuid5(uuid.NAMESPACE_URL,f'{m["id"]}:{t:.0f}').hex,'time':round(t,1),'start':round(max(0,t-15),1),'end':round(min(duration,t+20),1),'kind':kind,'confidence':confidence,'evidence':str(data.get('evidence',''))[:700],'included':confidence>=.75 and kind!='possible_goal'};events.append(event)
   m['events']=dedup(events);m['analysisComplete']=True;metrics['modelUsage']=usage;metrics['scoutCandidates']=len(all_events);metrics['deepCandidates']=len(candidates);metrics['analysisSeconds']=round(time.time()-started,2);lease=heartbeat(m,lease,'selection')
  clips=choose(m['events'],m['length']);m['note']=f'{len(clips)} sequences selected';lease=heartbeat(m,lease,'selection')
  if not clips:
   m['note']='No high-confidence clips selected. Review candidates or add a moment.';m['error']=None;lease=heartbeat(m,lease,'needs_review');return
  select_music(m);m['note']='Cutting clips and mixing music';lease=heartbeat(m,lease,'rendering');render_start=time.time();final,output_duration,selected=render(source,directory,m,clips)
  key=f"matches/{m['owner']}/{m['id']}/reel-r{m['revision']}.mp4";s3.upload_file(str(final),BUCKET,key,ExtraArgs={'ContentType':'video/mp4','ContentDisposition':'attachment; filename="touchline-reel.mp4"'});s3.upload_file(str(directory/'music-credits.txt'),BUCKET,key+'.credits.txt',ExtraArgs={'ContentType':'text/plain'});m['reelKey']=key;m['reelDuration']=output_duration;metrics['renderSeconds']=round(time.time()-render_start,2);metrics['lastRunSeconds']=round(time.time()-started,2);metrics['completedAt']=time.time();metrics['renderedClips']=selected;metrics['outputBytes']=final.stat().st_size;m['metrics']=metrics;m['error']=None;m['note']='Your reel is ready.';m['attempts']=0;lease=heartbeat(m,lease,'ready');logging.info('Completed %s: source=%.2fs reel=%.2fs',m['id'],duration,output_duration)
 except LostLease:logging.warning('Lease lost for %s; another worker owns it.',m['id'])
 except Exception as e:
  logging.exception('Failed %s',m['id']);m['attempts']=m.get('attempts',0)+1;m['error']=str(e)[:1600];m['note']='Saved analysis will be reused when retried.'
  stage='failed' if isinstance(e,InvalidVideo) or m['attempts']>=3 else 'queued'
  try:heartbeat(m,lease,stage)
  except LostLease:pass
 finally:
  # Canonical video, events, checkpoints and output are durable in S3/DynamoDB.
  # Keeping no match files at rest on shared compute prevents disk exhaustion.
  shutil.rmtree(directory,ignore_errors=True)

def scan():
 args={'TableName':TABLE};items=[]
 while True:
  r=ddb.scan(**args);items.extend(r.get('Items',[]))
  if 'LastEvaluatedKey' not in r:return items
  args['ExclusiveStartKey']=r['LastEvaluatedKey']

def main():
 while True:
  try:
   items=scan();now=time.time()
   for i in sorted(items,key=lambda i:float(i.get('updated',{'N':'0'})['N'])):
    stage=i['stage']['S']
    if stage=='discarded':
     m=json.loads(i['doc']['S']);prefix=f"matches/{m['owner']}/{m['id']}/"
     for page in s3.get_paginator('list_objects_v2').paginate(Bucket=BUCKET,Prefix=prefix):
      objs=[{'Key':x['Key']} for x in page.get('Contents',[])]
      if objs:s3.delete_objects(Bucket=BUCKET,Delete={'Objects':objs})
     continue
    if not (stage=='queued' or stage in ['ingestion','analysis','selection','rendering'] and float(i.get('lease',{'N':'0'})['N'])<now):continue
    lease=now+1800
    try:ddb.update_item(TableName=TABLE,Key={'id':i['id']},UpdateExpression='SET stage=:s, lease=:l',ConditionExpression='revision=:r AND (stage=:q OR (lease<:now AND stage IN (:i,:a,:c,:v)))',ExpressionAttributeValues={':s':{'S':'ingestion'},':l':{'N':str(lease)},':r':i['revision'],':q':{'S':'queued'},':now':{'N':str(now)},':i':{'S':'ingestion'},':a':{'S':'analysis'},':c':{'S':'selection'},':v':{'S':'rendering'}})
    except ClientError:continue
    process(i,lease);break
  except Exception:logging.exception('Worker polling failed')
  time.sleep(10)
if __name__=='__main__':main()
