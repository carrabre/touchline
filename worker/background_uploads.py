"""Finalize native uploads from durable S3 parts, independently of app callbacks."""
import json,math,time
from botocore.exceptions import ClientError
CHUNK=16*1024**2

def finalize_background_upload(m,s3,ddb,bucket,table):
 if not m.get('backgroundUpload') or m.get('recording') or m['status']!='uploading':return False
 try:
  uploaded=[]
  for page in s3.get_paginator('list_parts').paginate(Bucket=bucket,Key=m['key'],UploadId=m['uploadId']):uploaded.extend(page.get('Parts',[]))
  expected=math.ceil(m['size']/CHUNK)
  if len(uploaded)!=expected:return False
  uploaded.sort(key=lambda p:p['PartNumber'])
  if any(p['PartNumber']!=i+1 or p['Size']!=(CHUNK if i<expected-1 else m['size']-CHUNK*i) for i,p in enumerate(uploaded)):return False
  s3.complete_multipart_upload(Bucket=bucket,Key=m['key'],UploadId=m['uploadId'],MultipartUpload={'Parts':[{'PartNumber':p['PartNumber'],'ETag':p['ETag']} for p in uploaded]})
 except ClientError as error:
  if error.response['Error']['Code']!='NoSuchUpload':raise
  # An earlier completion may have succeeded before the database update.
  try:
   if s3.head_object(Bucket=bucket,Key=m['key'])['ContentLength']!=m['size']:return False
  except ClientError:return False
 m={**m,'status':'queued','note':'Upload received. Processing continues without the app.'}
 try:
  ddb.update_item(TableName=table,Key={'id':{'S':m['id']}},UpdateExpression='SET doc=:d, stage=:q, lease=:l, updated=:u',ConditionExpression='stage=:s AND revision=:r',ExpressionAttributeValues={':d':{'S':json.dumps(m)},':q':{'S':'queued'},':l':{'N':'0'},':u':{'N':str(int(time.time()*1000))},':s':{'S':'uploading'},':r':{'N':str(m['revision'])}})
 except ClientError as error:
  if error.response['Error']['Code']=='ConditionalCheckFailedException':return False
  raise
 return True
