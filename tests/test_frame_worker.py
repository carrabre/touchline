"""Exercise empty-scout recovery through the real worker state machine."""
import contextlib
import os,sys,pathlib,tempfile,subprocess,json,shutil,unittest,copy
from unittest.mock import patch,MagicMock
os.environ.setdefault('MEDIA_BUCKET','local-test-only');os.environ.setdefault('MATCH_TABLE','local-test-only');os.environ.setdefault('AWS_EC2_METADATA_DISABLED','true');os.environ.setdefault('AWS_DEFAULT_REGION','us-east-1');os.environ.setdefault('WORK_DIR',tempfile.mkdtemp());os.environ['AWS_ACCESS_KEY_ID']='local-only';os.environ['AWS_SECRET_ACCESS_KEY']='local-only'
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'worker'))
import worker
class FrameWorkerTests(unittest.TestCase):
 def exercise(self,confirmed,net=False):
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
   net_events=[{'id':'verified','time':1,'start':0,'end':2,'kind':'goal','confidence':.62,'evidence':'Two independent close-ups see ball inside net','verified':True,'included':True}]
   net_context=patch.object(worker,'analyze_nets',return_value=(net_events,101)) if net else contextlib.nullcontext()
   with net_context,patch.object(worker,'ROOT',root),patch.object(worker,'heartbeat',side_effect=heartbeat),patch.object(worker,'load_checkpoint',return_value=None),patch.object(worker,'checkpoint'),patch.object(worker,'vision',return_value=({'events':[]},{})),patch.object(worker.frame_goals,'classify',return_value={}),patch.object(worker.frame_goals,'scout',return_value=candidate),patch.object(worker.frame_goals,'review',return_value=assessment),patch.object(worker,'select_music'),patch.object(worker,'render',side_effect=render),patch.object(worker,'s3',MagicMock()):
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
 def test_two_model_net_confirmation_reaches_render_despite_lower_raw_score(self):
  m=self.exercise(True,net=True);self.assertEqual(m['status'],'ready')
  self.assertTrue(m['events'][0]['verified']);self.assertTrue(m['events'][0]['included'])
  self.assertEqual(m['events'][0]['confidence'],.62);self.assertEqual(len(m['metrics']['renderedClips']),1)
 def test_net_reanalysis_preserves_manual_goals_and_excludes_disagreements(self):
  m={'id':'net-test','revision':2,'status':'analysis','events':[{'id':'manual','time':5,'kind':'manual','manual':True,'included':True,'confidence':1}]};metrics={}
  def scan(detector,source,directory,start,length,cal):
   return {'rows':[{'side':0,'t':start+10,'confidence':.8}],'frames':360}
  def verify(client,source,directory,e,duration,cal,model_id=None,second_view=False,tie_break=False):
   t=e['time'];positive=t==10 and (second_view or tie_break) or t==40 and not (second_view or tie_break)
   return {'candidate':e,'model':worker.net_goals.MODEL,'secondView':second_view,'tieBreak':tie_break,'usage':{},'data':{'goal':positive,'uncertain':t==10 and not (second_view or tie_break) or t==40 and second_view,'time':t if positive else None,'confidence':.7,'evidenceTimes':[t],'observations':[{'time':t,'ball':'checked inside net'}],'evidence':'Visible ball position checked'}}
  with tempfile.TemporaryDirectory() as tmp,patch.object(worker,'heartbeat',side_effect=lambda doc,lease,stage=None:lease+1),patch.object(worker,'load_checkpoint',return_value=None),patch.object(worker,'checkpoint'),patch.object(worker.frame_goals,'classify',return_value={'stationary':True,'indoor':True}),patch.object(worker.net_goals,'calibrate',return_value={'supported':True}),patch.object(worker.net_goals,'ensure_model'),patch.object(worker.net_goals,'BallDetector'),patch.object(worker.net_goals,'scan_segment',side_effect=scan),patch.object(worker.net_goals,'verify',side_effect=verify) as verifier:
   events,lease=worker.analyze_nets(m,100,'source',pathlib.Path(tmp),90,metrics)
  self.assertEqual(len(events),3);self.assertEqual(events[0]['id'],'manual')
  self.assertTrue(events[1]['verified']);self.assertTrue(events[1]['included'])
  self.assertEqual(events[2]['reviewOutcome'],'unconfirmed');self.assertFalse(events[2]['included'])
  self.assertEqual(metrics['netVerifiedGoals'],1);self.assertGreater(lease,100);self.assertEqual(verifier.call_count,7)
if __name__=='__main__':unittest.main()
