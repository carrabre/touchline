"""Install only the Touchline worker in a capped Docker container via existing AWS SSM."""
import pathlib,json,subprocess,base64,time,zipfile,tempfile
ROOT=pathlib.Path(__file__).parent;INSTANCE='i-0f165410a7653c04e'
# AWS authentication must already be renewed; no credential files enter the instance.
archive=pathlib.Path(tempfile.gettempdir())/'touchline-soundtracks.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for file in (ROOT/'tracks').iterdir():z.write(file,'tracks/'+file.name)
subprocess.run(['aws','s3','cp',str(archive),'s3://touchline-media-977099028101-us-east-1/worker-assets/soundtracks-v1.zip','--only-show-errors'],check=True)
commands=['set -eu','mkdir -p /opt/touchline-worker /var/lib/touchline-worker','chmod 700 /var/lib/touchline-worker','chown 10001:10001 /var/lib/touchline-worker']
for name in ['Dockerfile','requirements.txt','worker.py','music.py','soundtracks.py']:
 data=base64.b64encode((ROOT/name).read_bytes()).decode();commands.append(f"printf '%s' '{data}' | base64 -d > /opt/touchline-worker/{name}")
commands += ['aws s3 cp s3://touchline-media-977099028101-us-east-1/worker-assets/soundtracks-v1.zip /opt/touchline-worker/soundtracks.zip --only-show-errors', 'python3 -m zipfile -e /opt/touchline-worker/soundtracks.zip /opt/touchline-worker']
commands+=['docker build -t touchline-worker:latest /opt/touchline-worker','docker rm -f touchline-worker 2>/dev/null || true','docker run -d --name touchline-worker --restart unless-stopped --network host --cpus 2 --memory 4g --pids-limit 128 --user 10001:10001 --cap-drop ALL --read-only --tmpfs /tmp:rw,noexec,nosuid,size=256m --security-opt no-new-privileges --log-opt max-size=10m --log-opt max-file=3 -e MEDIA_BUCKET=touchline-media-977099028101-us-east-1 -e MATCH_TABLE=touchline-matches -v /var/lib/touchline-worker:/data touchline-worker:latest','docker inspect --format "{{.State.Status}}" touchline-worker']
p=subprocess.run(['aws','ssm','send-command','--instance-ids',INSTANCE,'--document-name','AWS-RunShellScript','--parameters',json.dumps({'commands':commands}),'--timeout-seconds','1800','--output','json'],capture_output=True,text=True,check=True);result=json.loads(p.stdout);print(json.dumps({'commandId':result['Command']['CommandId'],'instanceId':INSTANCE}))
