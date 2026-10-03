"""Real FFmpeg tests; no claim of production or learned soccer detection quality."""
import os,sys,pathlib,tempfile,unittest,subprocess,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'worker'))
os.environ.setdefault('MEDIA_BUCKET','local-test-only');os.environ.setdefault('MATCH_TABLE','local-test-only');os.environ.setdefault('AWS_EC2_METADATA_DISABLED','true');os.environ.setdefault('AWS_DEFAULT_REGION','us-east-1');os.environ.setdefault('WORK_DIR',tempfile.mkdtemp())
# Instantiating clients does not make requests. Dummy credentials isolate the local tests.
os.environ['AWS_ACCESS_KEY_ID']='local-only';os.environ['AWS_SECRET_ACCESS_KEY']='local-only'
from worker import choose,dedup,extract,probe,InvalidVideo,render,vision,LITE,review_candidates,review_window
from music import compose
from soundtracks import select_music,TRACKS
class MediaTests(unittest.TestCase):
 def test_late_goal_candidate_includes_attacking_sequence(self):
  # Real regression: the scout returned 3693, but the goal occurred near 3663.
  start,length=review_window(3693,5749.44)
  self.assertLessEqual(start,3663-15)
  self.assertGreaterEqual(start+length,3693+20)
 def test_review_context_stays_within_source(self):
  for candidate,duration in [(3,100),(98,100),(1,2)]:
   start,length=review_window(candidate,duration)
   self.assertGreaterEqual(start,0)
   self.assertGreater(length,0)
   self.assertLessEqual(start+length,duration)
 def test_music_retry_and_regeneration(self):
  m={'revision':0,'music':'random'}
  first,_=select_music(m)
  self.assertEqual(select_music(m)[0]['id'],first['id'])
  m['revision']=1
  self.assertNotEqual(select_music(m)[0]['id'],first['id'])
  for track in TRACKS:
   m['revision']+=1;m['music']=track['id']
   self.assertEqual(select_music(m)[0]['id'],track['id'])
   self.assertIn('CC-BY 4.0',m['renderMusic']['credits'])

 def test_model_json_with_trailing_commentary(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   video=pathlib.Path(d)/'clip.mp4';video.write_bytes(b'test')
   response={'output':{'message':{'content':[{'text':'```json\n{"events": []}\n```\nNotes: {"visibility":"low"}'}]}},'usage':{}}
   with patch('worker.model.converse',return_value=response):
    self.assertEqual(vision(video,'test',LITE)[0],{'events':[]})

 def test_model_bare_event_array(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   video=pathlib.Path(d)/'clip.mp4';video.write_bytes(b'test')
   event={'time':10,'kind':'save','confidence':.8,'evidence':'keeper intervention'}
   response={'output':{'message':{'content':[{'text':json.dumps([event])}]}},'usage':{}}
   with patch('worker.model.converse',return_value=response):
    self.assertEqual(vision(video,'test',LITE)[0],{'events':[event]})
 def test_goal_scout_and_review_schemas_on_same_model(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   video=pathlib.Path(d)/'clip.mp4';video.write_bytes(b'test')
   scout={'goals':[{'time':10,'confirmed':True,'evidence':'ball enters net'},{'time':30,'confirmed':False,'evidence':'ball obscured'}]}
   review={'worthwhile':True,'time':20,'kind':'goal','confidence':.9,'evidence':'net and celebration'}
   for mode,document in [('scout',scout),('review',review)]:
    response={'output':{'message':{'content':[{'text':json.dumps(document)}]}},'usage':{}}
    with patch('worker.model.converse',return_value=response):
     data,_=vision(video,'test',LITE,mode=mode)
     if mode=='scout':self.assertEqual([e['kind'] for e in data['events']],['goal','possible_goal'])
     else:self.assertTrue(data['worthwhile'])
 def test_overlap_and_duplicate_merge(self):
  events=[{'time':30,'start':18,'end':39,'confidence':.9,'included':True,'kind':'goal'}, {'time':45,'start':33,'end':54,'confidence':.8,'included':True,'kind':'save'}, {'time':32,'start':20,'end':41,'confidence':.5,'included':False,'kind':'possible_goal'}]
  self.assertEqual(len(dedup(events)),2);self.assertEqual(choose(events,180)[0]['end'],54);self.assertEqual(len(choose(events,180)),1)
 def test_all_goals_survive_short_reel_budget(self):
  goals=[{'id':str(i),'time':i*40,'start':i*40,'end':i*40+25,'confidence':.9,'included':True,'kind':'goal'} for i in range(6)]
  self.assertEqual(len(choose(goals,90)),6)
  self.assertEqual(sum(e['end']-e['start'] for e in choose(goals,90)),150)
  goals[0]['included']=False
  self.assertEqual(len(choose(goals,90)),5)
 def test_deleted_upload_cleanup_is_scoped_to_its_own_media(self):
  from unittest.mock import patch,MagicMock
  from worker import cleanup_discarded
  fake=MagicMock();fake.get_paginator.return_value.paginate.return_value=[{'Contents':[{'Key':'matches/uploader/game/source'},{'Key':'matches/uploader/game/reel-r0.mp4'}]}]
  with patch('worker.s3',fake):cleanup_discarded({'owner':'uploader','id':'game','key':'matches/uploader/game/source','uploadId':'pending'})
  fake.abort_multipart_upload.assert_called_once_with(Bucket='local-test-only',Key='matches/uploader/game/source',UploadId='pending')
  fake.get_paginator.return_value.paginate.assert_called_once_with(Bucket='local-test-only',Prefix='matches/uploader/game/')
  self.assertEqual(len(fake.delete_objects.call_args.kwargs['Delete']['Objects']),2)
 def test_thirty_goals_and_manual_goals_survive_every_length(self):
  for kind,manual in [('goal',False),('manual',True)]:
   goals=[{'id':str(i),'time':i*40+15,'start':i*40,'end':i*40+35,'confidence':.9,'included':True,'kind':kind,'manual':manual} for i in range(30)]
   for target in [90,180,240]:
    clips=choose(goals,target)
    self.assertEqual(len(clips),30)
    self.assertEqual(sum(e['end']-e['start'] for e in clips),1050)
   goals[0]['included']=False
   self.assertEqual(len(choose(goals,90)),29)
 def test_real_thirty_clip_render(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);source=p/'source.mp4'
   subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','testsrc2=size=160x90:rate=15:duration=90','-c:v','libx264','-pix_fmt','yuv420p','-y',str(source)],check=True)
   events=[{'id':str(i),'time':i*3+.5,'start':i*3,'end':i*3+1,'confidence':1,'included':True,'kind':'goal'} for i in range(30)]
   m={'title':'30 goals · render capacity test','labels':True,'music':'titan','revision':0}
   out,seconds,clips=render(source,p,m,choose(events,90))
   self.assertEqual(len(clips),30)
   self.assertAlmostEqual(seconds,30,delta=1)
   info,_,_=probe(out)
   self.assertEqual(info['streams'][0]['codec_name'],'h264')
   self.assertTrue(any(x['codec_name']=='aac' for x in info['streams']))
   dest=os.environ.get('THIRTY_GOAL_OUTPUT')
   if dest:__import__('shutil').copy(out,dest)
 def test_no_goal_candidate_dropped_at_review_limit(self):
  goals=[{'time':i*30,'kind':'goal','confidence':.9} for i in range(45)]
  others=[{'time':2000+i*30,'kind':'save','confidence':.8} for i in range(50)]
  reviewed=review_candidates(goals+others)
  self.assertEqual(sum(e['kind']=='goal' for e in reviewed),45)
  self.assertEqual(sum(e['kind']=='save' for e in reviewed),40)
 def test_excluded_clips_and_duration_budget(self):
  e=[{'time':i*30,'start':i*30,'end':i*30+20,'confidence':.9-i*.01,'included':i<5,'kind':'save'} for i in range(6)]
  self.assertEqual(len(choose(e,60)),3);self.assertLessEqual(sum(x['end']-x['start'] for x in choose(e,60)),60)
 def test_real_render_and_slow_timestamps(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);source=os.environ.get('SOCCER_SOURCE')
   if not source:self.skipTest('Set SOCCER_SOURCE to an authorized real video.')
   slow=p/'slow.mp4';extract(source,slow,60,8,True);self.assertAlmostEqual(probe(slow)[1],16,delta=.6)
   # Container smoke clips are manually selected here, not automatically detected highlights.
   m={'title':'Touchline · Render validation','labels':True,'events':[]};clips=[{'id':'test','time':68,'start':60,'end':72,'kind':'manual'},{'id':'test2','time':86,'start':80,'end':90,'kind':'manual'}]
   out,seconds,_=render(source,p,m,clips);self.assertAlmostEqual(seconds,22,delta=.5);info,_,_=probe(out);self.assertEqual(info['streams'][0]['codec_name'],'h264');self.assertTrue(any(x['codec_name']=='aac' for x in info['streams']));self.assertGreater(out.stat().st_size,10000)
   dest=os.environ.get('SMOKE_OUTPUT');
   if dest:__import__('shutil').copy(out,dest)
if __name__=='__main__':unittest.main()
