"""Provision isolated Touchline resources with an existing authorized AWS CLI session.
Never prints secrets. Writes one ignored, mode-0600 bootstrap file for Sites configuration.
Does not create compute or change the existing instance's other services.
"""
import json,os,subprocess,pathlib
REGION='us-east-1';ACCOUNT='977099028101';BUCKET=f'touchline-media-{ACCOUNT}-{REGION}';TABLE='touchline-matches';USER='touchline-site';ROLE='golf-vision-model-host'
def aws(*args):
 p=subprocess.run(['aws',*args,'--region',REGION,'--output','json'],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr)
 return json.loads(p.stdout) if p.stdout.strip() else {}
def exists(*args):
 p=subprocess.run(['aws',*args,'--region',REGION],capture_output=True);return p.returncode==0
if not exists('s3api','head-bucket','--bucket',BUCKET):aws('s3api','create-bucket','--bucket',BUCKET)
aws('s3api','put-public-access-block','--bucket',BUCKET,'--public-access-block-configuration',json.dumps(dict(BlockPublicAcls=True,IgnorePublicAcls=True,BlockPublicPolicy=True,RestrictPublicBuckets=True)))
aws('s3api','put-bucket-encryption','--bucket',BUCKET,'--server-side-encryption-configuration',json.dumps({'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]}))
aws('s3api','put-bucket-cors','--bucket',BUCKET,'--cors-configuration',json.dumps({'CORSRules':[{'AllowedOrigins':['https://touchline-reels.carrabre.chatgpt.site','http://localhost:3000','http://127.0.0.1:3000'],'AllowedMethods':['PUT','GET','HEAD'],'AllowedHeaders':['*'],'ExposeHeaders':['ETag','Content-Length','Content-Range'],'MaxAgeSeconds':3600}]}))
aws('s3api','put-bucket-lifecycle-configuration','--bucket',BUCKET,'--lifecycle-configuration',json.dumps({'Rules':[{'ID':'Abandon-incomplete-uploads','Status':'Enabled','Filter':{'Prefix':'matches/'},'AbortIncompleteMultipartUpload':{'DaysAfterInitiation':7}},{'ID':'Expire-analysis-artifacts','Status':'Enabled','Filter':{'Prefix':'analysis/'},'Expiration':{'Days':14}}]}))
if not exists('dynamodb','describe-table','--table-name',TABLE):aws('dynamodb','create-table','--table-name',TABLE,'--attribute-definitions','AttributeName=id,AttributeType=S','--key-schema','AttributeName=id,KeyType=HASH','--billing-mode','PAY_PER_REQUEST')
policy={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['s3:ListBucket','s3:ListBucketMultipartUploads'],'Resource':f'arn:aws:s3:::{BUCKET}'},{'Effect':'Allow','Action':['s3:GetObject','s3:PutObject','s3:DeleteObject','s3:AbortMultipartUpload','s3:ListMultipartUploadParts'],'Resource':f'arn:aws:s3:::{BUCKET}/*'},{'Effect':'Allow','Action':['dynamodb:GetItem','dynamodb:PutItem','dynamodb:UpdateItem','dynamodb:Scan','dynamodb:DeleteItem'],'Resource':f'arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/{TABLE}'}]}
if not exists('iam','get-user','--user-name',USER):aws('iam','create-user','--user-name',USER)
aws('iam','put-user-policy','--user-name',USER,'--policy-name','TouchlineOnly','--policy-document',json.dumps(policy))
worker=json.loads(json.dumps(policy));worker['Statement'].append({'Effect':'Allow','Action':['bedrock:InvokeModel'],'Resource':[f'arn:aws:bedrock:us-east-1:{ACCOUNT}:inference-profile/us.amazon.nova-lite-v1:0',f'arn:aws:bedrock:us-east-1:{ACCOUNT}:inference-profile/us.amazon.nova-pro-v1:0','arn:aws:bedrock:us-*: :foundation-model/amazon.nova-lite-v1:0'.replace(': :','::'),'arn:aws:bedrock:us-*: :foundation-model/amazon.nova-pro-v1:0'.replace(': :','::')]})
aws('iam','put-role-policy','--role-name',ROLE,'--policy-name','TouchlineIsolatedMedia','--policy-document',json.dumps(worker))
secret=pathlib.Path('../../work/touchline-bootstrap.json').resolve()
if not secret.exists():
 key=aws('iam','create-access-key','--user-name',USER)['AccessKey'];secret.write_text(json.dumps({'MEDIA_ACCESS_KEY':key['AccessKeyId'],'MEDIA_SECRET_KEY':key['SecretAccessKey'],'MEDIA_BUCKET':BUCKET,'MATCH_TABLE':TABLE}));os.chmod(secret,0o600)
print(json.dumps({'bucket':BUCKET,'table':TABLE,'secretFile':str(secret),'workerRole':ROLE}))
