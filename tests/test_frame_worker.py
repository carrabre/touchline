"""Exercise empty-scout recovery through the real worker state machine."""
import os,sys,pathlib,tempfile,subprocess,json,shutil,unittest,copy
from unittest.mock import patch,MagicMock
os.environ.setdefault('MEDIA_BUCKET','local-test-only');os.environ.setdefault('MATCH_TABLE','local-test-only');os.environ.setdefault('AWS_EC2_METADATA_DISABLED','true');os.environ.setdefault('AWS_DEFAULT_REGION','us-east-1');os.environ.setdefault('WORK_DIR',tempfile.mkdtemp());os.environ['AWS_ACCESS_KEY_ID']='local-only';os.environ['AWS_SECRET_ACCESS_KEY']='local-only'
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'worker'))
import worker
class FrameWorkerTests(unittest.TestCase):
 def exercise(self,confirmed):
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp);directory=root/'game';directory.mkdir();source=directory/'source'
   subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=green:size=64x64:duration=2:rate=10','-c:v','libx264','-f','mp4','-y',str(source)],capture_output=True,check=True)
   m={'id':'game','owner':'owner','revision':1,'status':'queued','key':'matches/owner/game/source','size':source.stat().st_size,'length':180,'title':'Test','mime':'video/mp4','labels':True}
   saves=[]
   def heartbeat(doc,lease,stage=None):
    doc['status']=stage or doc['status'];saves.append(copy.deepcopy(doc));return lease+1
   def render(src,path,match,clips):
    (path/'music-credits.txt').write_text('Test credits');return src,2,clips
   candidate={'start':0,'duration':2,'data':{'observations':[{'time':1,'action':'shot near net'}],'events':[{'time':1,'kind':'possible_goal','confidence':.2,'evidence':'shot, ball obscured'}]},'usage':{}}
   assessment={'data':{'observations':[{'time':1,'action':'outcome checked'}],'worthwhile':confirmed,'time':1,'kind':'goal','confidence':.95 if confirmed else 0,'evidence':'Ball enters net and players reset.' if confirmed else 'Ball/goal line obscured; could not establish outcome.'},'usage':{}}
   with patch.object(worker,'ROOT',root),patch.object(worker,'heartbeat',side_effect=heartbeat),patch.object(worker,'load_checkpoint',return_value=None),patch.object(worker,'checkpoint'),patch.object(worker,'vision',return_value=({'events':[]},{})),patch.object(worker.frame_goals,'classify',return_value={}),patch.object(worker.frame_goals,'scout',return_value=candidate),patch.object(worker.frame_goals,'review',return_value=assessment),patch.object(worker,'select_music'),patch.object(worker,'render',side_effect=render),patch.object(worker,'s3',MagicMock()):
    worker.process({'doc':{'S':json.dumps(m)}},100)
   self.assertTrue(saves);return saves[-1]
 def test_ambiguous_empty_scout_stays_reviewable_and_unselected(self):
  m=self.exercise(False);self.assertEqual(m['status'],'needs_review');self.assertEqual(len(m['events']),1)
  e=m['events'][0];self.assertFalse(e['included']);self.assertEqual(e['kind'],'possible_goal');self.assertEqual(e['reviewOutcome'],'unconfirmed')
  self.assertIn('could not be confirmed',m['note']);self.assertEqual(m['metrics']['frameWindows'],1)
 def test_independently_confirmed_recovered_goal_reaches_reel(self):
  m=self.exercise(True);self.assertEqual(m['status'],'ready');self.assertEqual(len(m['events']),1)
  e=m['events'][0];self.assertTrue(e['included']);self.assertEqual(e['kind'],'goal');self.assertEqual(e['time'],1)
  self.assertEqual(m['metrics']['renderedClips'][0]['time'],1)
if __name__=='__main__':unittest.main()
