"""Native multipart completion must not depend on the phone calling finish."""
import pathlib,sys,unittest,copy
from unittest.mock import MagicMock
from botocore.exceptions import ClientError
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'worker'))
from background_uploads import finalize_background_upload,CHUNK
class BackgroundUploadTests(unittest.TestCase):
 def fixtures(self):
  m={'id':'native-job','key':'matches/test/native-job/source','owner':'test','uploadId':'multipart','size':CHUNK+4,'status':'uploading','revision':0,'backgroundUpload':True}
  s3=MagicMock();ddb=MagicMock();s3.get_paginator.return_value.paginate.return_value=[{'Parts':[{'PartNumber':1,'Size':CHUNK,'ETag':'one'},{'PartNumber':2,'Size':4,'ETag':'two'}]}]
  return m,s3,ddb
 def test_completed_file_queues_without_app_callback(self):
  m,s,d=self.fixtures();self.assertTrue(finalize_background_upload(m,s,d,'bucket','table'))
  self.assertEqual(m['status'],'uploading');s.complete_multipart_upload.assert_called_once();args=d.update_item.call_args.kwargs
  self.assertEqual(args['ExpressionAttributeValues'][':q']['S'],'queued');self.assertIn('stage=:s AND revision=:r',args['ConditionExpression'])
 def test_partial_or_wrong_sized_uploads_wait(self):
  for parts in [[{'PartNumber':1,'Size':CHUNK,'ETag':'one'}],[{'PartNumber':1,'Size':CHUNK,'ETag':'one'},{'PartNumber':2,'Size':3,'ETag':'two'}],[{'PartNumber':2,'Size':CHUNK,'ETag':'one'},{'PartNumber':3,'Size':4,'ETag':'two'}]]:
   m,s,d=self.fixtures();s.get_paginator.return_value.paginate.return_value=[{'Parts':parts}]
   self.assertFalse(finalize_background_upload(m,s,d,'bucket','table'));s.complete_multipart_upload.assert_not_called();d.update_item.assert_not_called()
 def test_browser_and_recording_jobs_are_not_auto_finished(self):
  for change in [{'backgroundUpload':False},{'recording':True},{'status':'discarded'}]:
   m,s,d=self.fixtures();m.update(change);self.assertFalse(finalize_background_upload(m,s,d,'bucket','table'));s.complete_multipart_upload.assert_not_called()
 def test_completion_retry_recovers_existing_object(self):
  m,s,d=self.fixtures();s.get_paginator.return_value.paginate.side_effect=ClientError({'Error':{'Code':'NoSuchUpload'}},'ListParts');s.head_object.return_value={'ContentLength':m['size']}
  self.assertTrue(finalize_background_upload(m,s,d,'bucket','table'));s.complete_multipart_upload.assert_not_called()
 def test_delete_race_does_not_resurrect_game(self):
  m,s,d=self.fixtures();d.update_item.side_effect=ClientError({'Error':{'Code':'ConditionalCheckFailedException'}},'UpdateItem')
  self.assertFalse(finalize_background_upload(m,s,d,'bucket','table'))
if __name__=='__main__':unittest.main()
