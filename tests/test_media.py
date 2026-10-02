"""Real FFmpeg tests; no claim of production or learned soccer detection quality."""
import os,sys,pathlib,tempfile,unittest,subprocess,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'worker'))
os.environ.setdefault('MEDIA_BUCKET','local-test-only');os.environ.setdefault('MATCH_TABLE','local-test-only');os.environ.setdefault('AWS_EC2_METADATA_DISABLED','true');os.environ.setdefault('AWS_DEFAULT_REGION','us-east-1');os.environ.setdefault('WORK_DIR',tempfile.mkdtemp())
# Instantiating clients does not make requests. Dummy credentials isolate the local tests.
os.environ['AWS_ACCESS_KEY_ID']='local-only';os.environ['AWS_SECRET_ACCESS_KEY']='local-only'
from worker import choose,dedup,extract,probe,InvalidVideo,render,vision,LITE
from music import compose
class MediaTests(unittest.TestCase):
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
 def test_overlap_and_duplicate_merge(self):
  events=[{'time':30,'start':18,'end':39,'confidence':.9,'included':True,'kind':'goal'}, {'time':45,'start':33,'end':54,'confidence':.8,'included':True,'kind':'save'}, {'time':32,'start':20,'end':41,'confidence':.5,'included':False,'kind':'possible_goal'}]
  self.assertEqual(len(dedup(events)),2);self.assertEqual(choose(events,180)[0]['end'],54);self.assertEqual(len(choose(events,180)),1)
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
