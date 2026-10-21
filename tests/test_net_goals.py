"""Net geometry proposes candidates; independent evidence decides the score."""
import pathlib,sys,tempfile,unittest,json,subprocess,hashlib,copy
from unittest.mock import MagicMock,patch
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'worker'))
import net_goals as n
class NetGoalTests(unittest.TestCase):
 def test_model_hash_mismatch_cannot_install_detector(self):
  with tempfile.TemporaryDirectory() as tmp:
   s3=MagicMock();s3.download_file.side_effect=lambda bucket,key,file:pathlib.Path(file).write_bytes(b'corrupt')
   with self.assertRaisesRegex(RuntimeError,'SHA-256'):n.ensure_model(s3,'test',tmp)
   self.assertFalse((pathlib.Path(tmp)/'models/rfdetr-nano.onnx').exists())
 def test_fast_single_detection_and_thirty_goals_are_all_reviewed(self):
  rows=[{'side':i%2,'t':i*40+.125,'confidence':.7} for i in range(30)]
  candidates=n.candidates(rows);self.assertEqual(len(candidates),30)
  self.assertEqual([e['time'] for e in candidates],[r['t'] for r in rows])
 def test_long_ball_episode_is_split_without_losing_detections(self):
  rows=[{'side':0,'t':i/6,'confidence':.5} for i in range(400)]
  chunks=n.candidates(rows);self.assertGreater(len(chunks),1)
  self.assertEqual(sum(c['detections'] for c in chunks),len(rows))
  self.assertTrue(all(c['lastSeen']-c['time']<8 for c in chunks))
  self.assertEqual(len(set(c['episode'] for c in chunks)),1)
 def test_independent_agreement_never_uses_low_confidence_as_proof(self):
  primary={'data':{'goal':True,'uncertain':False,'confidence':.82,'time':318.2,'evidenceTimes':[318.2,318.4]}}
  secondary={'data':{'goal':True,'uncertain':False,'confidence':.74,'time':318.5,'evidenceTimes':[318.5]}}
  self.assertTrue(n.agreement(primary,secondary))
  for change in [{'goal':False},{'uncertain':True},{'confidence':.2},{'confidence':float('nan')},{'time':400},{'time':float('nan')},{'evidenceTimes':[]}]:
   changed=copy.deepcopy(secondary);changed['data'].update(change);self.assertFalse(n.agreement(primary,changed))
 def test_unrecognized_nets_use_general_camera_pipeline(self):
  self.assertEqual(n.propose_regions(np.zeros((864,1536,3),dtype=np.uint8)),[])
  self.assertFalse(n.calibrate(MagicMock(),'missing','unused',120,{'stationary':False,'indoor':True})['supported'])
 def test_native_crop_decode_covers_both_nets_and_source_timestamps(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp);source=p/'video.mp4'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=green:size=128x128:duration=3:rate=30','-c:v','libx264','-y',str(source)],capture_output=True,check=True)
   detector=MagicMock();detector.detect.return_value=[{'box':[10,10,15,15],'confidence':.8}]
   cal={'referenceSize':[128,128],'regions':[{'bounds':[0,0,60,60],'goalHeight':40},{'bounds':[64,64,124,124],'goalHeight':40}]}
   result=n.scan_segment(detector,source,p/'scan',1,2,cal)
   self.assertEqual(result['frames'],24);self.assertEqual({r['side'] for r in result['rows']},{0,1})
   self.assertTrue(all(1<=r['t']<3 for r in result['rows']))
   self.assertTrue(all(r['box'][0]>=64 for r in result['rows'] if r['side']==1))
   detector.detect.return_value=[{'box':[0,0,30,30],'confidence':.9}]
   result=n.scan_segment(detector,source,p/'head',1,2,cal);self.assertEqual(result['rows'],[])
 def test_dense_verifier_message_limits_and_source_clock(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp);source=p/'video.mp4'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=green:size=128x128:duration=3:rate=30','-c:v','libx264','-y',str(source)],capture_output=True,check=True)
   cal={'referenceSize':[128,128],'regions':[{'bounds':[0,0,60,60],'goalHeight':40}]}
   e={'side':0,'time':1,'lastSeen':1.2,'peakTime':1}
   d={'goal':True,'uncertain':False,'confidence':.8,'time':1,'evidenceTimes':[1],'evidence':'Ball crosses opening and contacts rear net.','observations':[{'time':1,'ball':'inside net'}]}
   client=MagicMock();client.converse.return_value={'output':{'message':{'content':[{'text':json.dumps(d)}]}}}
   self.assertTrue(n.verify(client,source,p/'review',e,3,cal)['data']['goal'])
   messages=client.converse.call_args.kwargs['messages'];self.assertGreater(len(messages),1)
   self.assertTrue(all(sum('image' in c for c in m['content'])<=20 for m in messages))
   d['time']=99;client.converse.return_value={'output':{'message':{'content':[{'text':json.dumps(d)}]}}}
   r=n.verify(client,source,p/'review',e,3,cal);self.assertFalse(r['data']['goal']);self.assertTrue(r['data']['uncertain'])
 def test_only_ball_sized_objects_near_the_localized_net_reach_review(self):
  cal={'referenceSize':[1000,500],'regions':[{'bounds':[50,250,250,400],'anchor':[100,300,110,330],'goalHeight':40}]}
  ball={'side':0,'t':10,'box':[120,310,125,315],'confidence':.12}
  head={**ball,'box':[120,300,150,330]}
  passing={**ball,'box':[220,310,225,315]}
  self.assertEqual(n.filter_sightings([ball,head,passing],cal,1000,500),[ball])
  scaled={**ball,'box':[v*2 for v in ball['box']]}
  self.assertEqual(n.filter_sightings([scaled],cal,2000,1000),[scaled])
 def test_right_goal_review_includes_the_incoming_court_side(self):
  region={'anchor':[1181,519,1336,638],'goalHeight':119,'bounds':[1109,435,1536,715]}
  wide=n.review_region(region,[1536,864]);x,y,r,b=region['anchor'];a,top,c,bottom=wide['bounds']
  self.assertGreater(x-a,c-r);self.assertLess(a,1100)
  close=n.review_region(region,[1536,864],True);self.assertLess(close['bounds'][2]-close['bounds'][0],c-a)
 def test_uncertainty_does_not_veto_two_independent_direct_positives(self):
  uncertain={'data':{'goal':False,'uncertain':True,'confidence':.35,'time':None,'evidenceTimes':[]}}
  first={'data':{'goal':True,'uncertain':False,'confidence':.7,'time':318.4,'evidenceTimes':[318.4]}}
  second={'data':{'goal':True,'uncertain':False,'confidence':.8,'time':318.5,'evidenceTimes':[318.5]}}
  self.assertIsNone(n.consensus([uncertain,first]));self.assertEqual(n.consensus([uncertain,first,second]),[first,second])
  self.assertIsNone(n.consensus([uncertain,uncertain,first]))
if __name__=='__main__':unittest.main()
