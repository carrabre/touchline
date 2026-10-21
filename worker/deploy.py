"""Deploy a checksummed Touchline bundle through S3 and a small SSM command."""
import pathlib,json,subprocess,hashlib,zipfile,tempfile,sys
ROOT=pathlib.Path(__file__).parent;INSTANCE='i-0f165410a7653c04e';BUCKET='touchline-media-977099028101-us-east-1'
# Never embed the whole source tree in SendCommand: SSM limits documents to 97KB.
# Credentials remain with the signed-in CLI / instance role, outside the bundle.
archive=pathlib.Path(tempfile.gettempdir())/'touchline-worker-bundle.zip'
files=['Dockerfile','requirements.txt','worker.py','music.py','soundtracks.py','background_uploads.py','frame_goals.py','net_goals.py','MODEL_NOTICE.md','RF_DETR_LICENSE.txt']
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for name in files:z.write(ROOT/name,name)
 for file in (ROOT/'tracks').iterdir():
  if file.is_file():z.write(file,'tracks/'+file.name)
with archive.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
key=f'worker-assets/bundles/worker-{digest}.zip'
subprocess.run(['aws','s3','cp',str(archive),f's3://{BUCKET}/{key}','--only-show-errors'],check=True)
remote='/opt/touchline-worker-bundle.zip'
commands=['set -eu','mkdir -p /opt/touchline-worker /var/lib/touchline-worker','chmod 700 /var/lib/touchline-worker','chown 10001:10001 /var/lib/touchline-worker',f'aws s3 cp s3://{BUCKET}/{key} {remote} --only-show-errors',f'''python3 -c "import hashlib,pathlib; p=pathlib.Path('{remote}'); assert hashlib.sha256(p.read_bytes()).hexdigest()=='{digest}', 'Worker bundle checksum mismatch'"''',f'python3 -m zipfile -e {remote} /opt/touchline-worker','docker build -t touchline-worker:latest /opt/touchline-worker','docker rm -f touchline-worker 2>/dev/null || true','docker run -d --name touchline-worker --restart unless-stopped --network host --cpus 2 --memory 4g --pids-limit 128 --user 10001:10001 --cap-drop ALL --read-only --tmpfs /tmp:rw,noexec,nosuid,size=256m --security-opt no-new-privileges --log-opt max-size=10m --log-opt max-file=3 -e MEDIA_BUCKET=touchline-media-977099028101-us-east-1 -e MATCH_TABLE=touchline-matches -v /var/lib/touchline-worker:/data touchline-worker:latest','docker inspect --format "{{.State.Status}}" touchline-worker',f'rm -f {remote}']
p=subprocess.run(['aws','ssm','send-command','--instance-ids',INSTANCE,'--document-name','AWS-RunShellScript','--parameters',json.dumps({'commands':commands}),'--timeout-seconds','1800','--output','json'],capture_output=True,text=True)
if p.returncode:
 print((p.stderr or 'AWS worker deployment request failed.')[:2000],file=sys.stderr);raise SystemExit(p.returncode)
result=json.loads(p.stdout);print(json.dumps({'commandId':result['Command']['CommandId'],'instanceId':INSTANCE,'bundleSHA256':digest}))
