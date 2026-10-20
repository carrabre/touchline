import io,json,pathlib,sys,tempfile,unittest,subprocess
from unittest.mock import MagicMock,patch
from PIL import Image
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'worker'))
import frame_goals as fg

def response(data):
 return {'output':{'message':{'content':[{'text':'```json\n'+json.dumps(data)+'\n```'}]}},'usage':{'inputTokens':12}}

class FrameGoalTests(unittest.TestCase):
 def test_complete_coverage_without_redundant_tail(self):
  for duration in [1,23.1,24,25,1198.031667,7200]:
   windows=list(fg.windows(duration));self.assertEqual(windows[0][0],0)
   self.assertAlmostEqual(windows[-1][0]+windows[-1][1],duration)
   for (start,length),(next_start,_) in zip(windows,windows[1:]):self.assertGreaterEqual(start+length-next_start,4)
 def test_invalid_or_moving_court_never_crops_away_play(self):
  for bounds in [None,[1.08,.44,1,.78],[0,.9,1,.1],[0,0,.2,1],[0,float('nan'),1,1],[0,0,1,1,1]]:
   self.assertEqual(fg.crop_bounds({'stationary':True,'indoor':True,'playingArea':bounds}),(0,0,1,1))
  for scene in [{'stationary':False,'indoor':True},{'stationary':True,'indoor':False}]:
   self.assertEqual(fg.crop_bounds({**scene,'playingArea':[0,.5,1,.9]}),(0,0,1,1))
 def test_stationary_indoor_crop_keeps_margin(self):
  a,b,c,d=fg.crop_bounds({'stationary':True,'indoor':True,'playingArea':[.08,.47,1,.88]})
  self.assertLess(a,.08);self.assertLess(b,.47);self.assertEqual(c,1);self.assertGreater(d,.88)
 def test_absolute_times_and_low_confidence_candidates_reach_review(self):
  result={'start':200,'duration':24,'data':{'events':[
   {'time':210.8,'confidence':.2,'kind':'possible_goal'},
   {'time':10.8,'confidence':.9,'kind':'goal'},
   {'time':224,'confidence':.9,'kind':'goal'},
   {'time':float('nan'),'confidence':.9,'kind':'goal'}]}}
  events=fg.events(result);self.assertEqual(len(events),1);self.assertEqual(events[0]['time'],210.8)
  self.assertTrue(events[0]['frameScout']);self.assertNotIn('included',events[0])
 def test_review_splits_images_and_rejects_wrong_clock(self):
  with tempfile.TemporaryDirectory() as temp:
   image=pathlib.Path(temp)/'frame.jpg';Image.new('RGB',(160,90)).save(image)
   frames=[(100+i,image) for i in range(40)]
   client=MagicMock();client.converse.return_value=response({'observations':[{'action':'shot and retrieval'}],'worthwhile':True,'time':120,'kind':'goal','confidence':.9})
   with patch('frame_goals.extract_frames',return_value=frames):
    result=fg.review(client,'source',temp,124,200,{})
   self.assertEqual(result['data']['time'],120)
   messages=client.converse.call_args.kwargs['messages'];self.assertEqual(len(messages),2)
   for message in messages:self.assertEqual(sum('image' in c for c in message['content']),20)
   self.assertTrue(any(c.get('text')=='Source video second 100.000' for c in messages[0]['content']))
   client.converse.return_value=response({'observations':[{'action':'shot'}],'worthwhile':True,'time':7,'kind':'goal','confidence':.9})
   with patch('frame_goals.extract_frames',return_value=frames),self.assertRaises(RuntimeError):fg.review(client,'source',temp,124,200,{})
 def test_scout_cannot_short_circuit_without_observations(self):
  with tempfile.TemporaryDirectory() as temp:
   file=pathlib.Path(temp)/'frame.jpg';Image.new('RGB',(160,90)).save(file)
   client=MagicMock();client.converse.return_value=response({'events':[]})
   with patch('frame_goals.extract_frames',return_value=[(0,file)]),self.assertRaises(RuntimeError):fg.scout(client,'source',temp,0,24,{})
 def test_all_thirty_goals_survive_uncertain_candidate_limit(self):
  goals=[{'time':i*40,'kind':'goal','confidence':.9,'included':True} for i in range(30)]
  uncertain=[{'time':2000+i*40,'kind':'possible_goal','confidence':.2,'included':False} for i in range(150)]
  result=fg.retain_review_events(goals+uncertain)
  self.assertEqual(sum(e['kind']=='goal' for e in result),30);self.assertEqual(len(result),100)
 def test_short_video_scene_samples_do_not_seek_past_last_second(self):
  with tempfile.TemporaryDirectory() as temp:
   source=pathlib.Path(temp)/'source.mp4'
   subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=green:size=64x64:duration=1.2:rate=30','-c:v','libx264','-y',str(source)],check=True,capture_output=True)
   client=MagicMock();client.converse.return_value=response({'stationary':False,'indoor':False,'playingArea':[0,0,1,1]})
   fg.classify(client,source,pathlib.Path(temp)/'scene',1.2)
   content=client.converse.call_args.kwargs['messages'][0]['content'];self.assertEqual(sum('image' in c for c in content),5)
 def test_real_short_tail_extract_is_labeled_with_source_time(self):
  with tempfile.TemporaryDirectory() as temp:
   source=pathlib.Path(temp)/'source.mp4'
   subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=green:size=64x64:duration=3:rate=10','-c:v','libx264','-y',str(source)],check=True,capture_output=True)
   frames=fg.extract_frames(source,pathlib.Path(temp)/'frames',2,1)
   self.assertTrue(frames);self.assertEqual(frames[0][0],2);self.assertTrue(all(2<=t<3 for t,f in frames))

if __name__=='__main__':unittest.main()
