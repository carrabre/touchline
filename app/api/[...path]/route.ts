import { runtimeConfig, requestOwner, createBrowserSession } from '@/lib/runtime-config';
import { db, scan, get, owned, put, s3, signed, parts, xmlValue, escapeXml, type Match, type Event } from '@/lib/aws';
import { isPublicMatch, publicMatch } from '@/lib/match-access';
import { musicChoices } from '@/lib/soundtracks';
const MAX=16*1024**3, CHUNK=16*1024**2;
const json=(d:unknown,status=200)=>Response.json(d,{status,headers:{'cache-control':'no-store'}});
async function handle(req:Request){
 try{
  const owner=requestOwner(req);
  if(owner)return await handleOwned(req,owner);
  if(req.method!=='GET')return json({error:'Open your match library to start a session.'},401);
  const session=createBrowserSession(req);
  const response=await handleOwned(req,session.owner);
  response.headers.set('set-cookie',session.cookie);
  return response;
 }catch(e){console.error('Browser session:',e instanceof Error?e.message:'Unavailable');return json({error:'Browser sessions are temporarily unavailable.'},503);}
}
async function handleOwned(req:Request,owner:string){
 try{
  if(!['GET','HEAD'].includes(req.method)){const origin=req.headers.get('origin');if(origin && origin!==new URL(req.url).origin)return json({error:'Cross-site request rejected.'},403);}
  const config=runtimeConfig();if(!config.MEDIA_ACCESS_KEY || !config.MEDIA_SECRET_KEY){if(req.method==='GET' && new URL(req.url).pathname==='/api/matches')return json({matches:[],available:false});return json({error:'Media processing is offline. The AWS connection must be restored before uploading.'},503);}
  const path=new URL(req.url).pathname.slice(5).split('/');
  if(path[0]==='sample' && path.length===1 && req.method==='POST'){
   const fixture=await get('validation-auto-goals-20261002');
   const validation=fixture?.metrics?.goalValidation as {missedGoals:number;extraGoals:number}|undefined;
   if(!fixture || fixture.status!=='ready' || !fixture.reelKey || validation?.missedGoals!==0 || validation?.extraGoals!==0)return json({error:'Sample reel unavailable.'},503);
   const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(owner+':verified-goals-sample-v1'));
   const id=Array.from(new Uint8Array(hash)).map(x=>x.toString(16).padStart(2,'0')).join('').slice(0,32);
   const existing=await get(id);if(existing && existing.status!=='discarded')return json({match:existing});
   const sample:Match={...fixture,id,owner,title:'Sample · All 3 goals',created:Date.now(),revision:0,
    events:fixture.events.map(e=>({...e,verified:true})),note:'Three source-verified goals. Final score: Belmont 1–2 Lexington.'};
   await put(sample);return json({match:sample});
  }
  if(path[0]!=='matches')return json({error:'Not found.'},404);
  if(path.length===1 && req.method==='GET'){
   const d=await scan({FilterExpression:'#s <> :discarded',ExpressionAttributeNames:{'#s':'stage'},ExpressionAttributeValues:{':discarded':{S:'discarded'}},Limit:100});
   const matches=(d.Items||[]).map((i:Record<string,any>)=>({...JSON.parse(i.doc.S),status:i.stage.S})).filter(isPublicMatch).sort((a:Match,b:Match)=>b.created-a.created);
   return json({available:true,matches:matches.map((m:Match)=>publicMatch(m,owner))});
  }
  if(path.length===1 && req.method==='POST'){
   const b=await req.json() as any;
   if(!b.title?.trim() || b.title.length>100 || !b.fingerprint || b.fingerprint.length>300 || !/^video\/(mp4|quicktime|webm|x-matroska)$/.test(b.mime)|| !Number.isSafeInteger(b.size)||b.size<0||b.size>MAX)return json({error:'Choose an MP4, MOV, WebM or MKV video under 16 GB.'},400);
   const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(owner+':'+b.fingerprint));let id=Array.from(new Uint8Array(hash)).map(x=>x.toString(16).padStart(2,'0')).join('').slice(0,32);
   let existing=await get(id);
   while(existing?.status==='discarded'){const retryHash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(existing.id+':reupload'));id=Array.from(new Uint8Array(retryHash)).map(x=>x.toString(16).padStart(2,'0')).join('').slice(0,32);existing=await get(id);}
   if(existing)return json({match:existing,chunkSize:CHUNK});
   const d=await scan({FilterExpression:'#o = :o AND (#s = :u OR #s = :q OR #s = :a OR #s = :r)',ExpressionAttributeNames:{'#o':'owner','#s':'stage'},ExpressionAttributeValues:{':o':{S:owner},':u':{S:'uploading'},':q':{S:'queued'},':a':{S:'analysis'},':r':{S:'rendering'}}});if((d.Items||[]).length>=3)return json({error:'Finish or discard an active upload before starting another (three at a time).'},429);
   const m:Match={id,owner,title:b.title.trim(),filename:String(b.filename).slice(0,200),mime:b.mime,size:b.size,key:`matches/${owner}/${id}/source`,recording:!!b.recording,created:Date.now(),status:'uploading',events:[],revision:0,length:180,labels:true};
   if(!m.recording){const x=await(await s3(m.key,'?uploads',{method:'POST',headers:{'content-type':m.mime}})).text();m.uploadId=xmlValue(x,'UploadId');if(!m.uploadId)throw new Error('Could not start upload.');}
   try{await put(m,'attribute_not_exists(id)');}catch(e){const saved=await get(id);if(!saved)throw e;if(m.uploadId)await s3(m.key,`?uploadId=${encodeURIComponent(m.uploadId)}`,{method:'DELETE'});return json({match:saved,chunkSize:CHUNK});}
   return json({match:m,chunkSize:CHUNK});
  }
  const action=path[2];
  const publicRead=req.method==='GET' && (!action || action==='credits');
  const m=publicRead?await get(path[1]):await owned(path[1],owner);
  if(!m || !isPublicMatch(m))throw new Error('Match not found.');
  if(action==='credits' && req.method==='GET'){if(!m.renderMusic?.credits)return json({error:'Music credits are available after rendering.'},404);return new Response(m.renderMusic.credits,{headers:{'content-type':'text/plain; charset=utf-8','content-disposition':'attachment; filename="touchline-music-credits.txt"','cache-control':'no-store'}});}
  if(!action && req.method==='GET')return json({match:publicMatch(m,owner),sourceUrl:m.status!=='uploading'?await signed(m.key):null,reelUrl:m.reelKey?await signed(m.reelKey,'GET','?response-content-disposition=attachment%3B%20filename%3D%22touchline-reel.mp4%22'):null});
  if(action==='parts' && req.method==='GET')return json({parts:m.recording?Array.from({length:m.parts||0},(_,i)=>({number:i+1})):await parts(m)});
  if(action==='part' && req.method==='POST'){
   if(m.status!=='uploading')return json({error:'This upload is already finished.'},409);
   const b=await req.json() as any,n=b.number;if(!Number.isSafeInteger(n)||n<1||n>2000)return json({error:'Invalid upload part.'},400);
   if(m.recording)return json({url:await signed(`${m.key}/segments/${String(n).padStart(5,'0')}`,'PUT')});
   if(n>Math.ceil(m.size/CHUNK))return json({error:'Unexpected upload part.'},400);
   return json({url:await signed(m.key,'PUT',`?partNumber=${n}&uploadId=${encodeURIComponent(m.uploadId!)}`)});
  }
  if(action==='recorded' && req.method==='POST'){
   if(m.status!=='uploading'||!m.recording)return json({error:'Recording is closed.'},409);
   const b=await req.json() as any;if(b.parts===m.parts)return json({match:m});if(!Number.isSafeInteger(b.parts)||b.parts!==((m.parts||0)+1)|| !Number.isSafeInteger(b.size)||b.size<=0||m.size+b.size>MAX)return json({error:'Recording segment out of sequence or storage limit reached.'},400);
   await s3(`${m.key}/segments/${String(b.parts).padStart(5,'0')}`,'',{method:'HEAD'});m.parts=b.parts;m.size+=b.size;await put(m,'stage = :s AND revision = :r',{':s':{S:'uploading'},':r':{N:String(m.revision)}}).catch(async()=>{throw new Error('Could not save recording progress.');});return json({match:m});
  }
  if(action==='finish' && req.method==='POST'){
   if(m.status!=='uploading')return json({match:m});
   if(m.recording){if(!m.parts)return json({error:'No saved recording segments.'},400);}else{
    let stored=false;try{const head=await s3(m.key,'',{method:'HEAD'});stored=Number(head.headers.get('content-length'))===m.size;}catch{}
    if(!stored){const p=await parts(m);if(p.length!==Math.ceil(m.size/CHUNK)||p.reduce((a,x)=>a+x.size,0)!==m.size||p.some((x,i)=>x.number!==i+1 || (i<p.length-1 && x.size!==CHUNK)))return json({error:'Upload is incomplete. Reselect the same file to resume.'},409);
    const xml='<CompleteMultipartUpload>'+p.map(x=>`<Part><PartNumber>${x.number}</PartNumber><ETag>${escapeXml(x.etag)}</ETag></Part>`).join('')+'</CompleteMultipartUpload>';
    const result=await(await s3(m.key,`?uploadId=${encodeURIComponent(m.uploadId!)}`,{method:'POST',body:xml,headers:{'content-type':'application/xml'}})).text();if(result.includes('<Error>'))throw new Error('Storage could not complete the upload. Please retry.');}
   }
   m.status='queued';m.note='Waiting for the media worker';await put(m,'stage = :s AND revision = :r',{':s':{S:'uploading'},':r':{N:String(m.revision)}});return json({match:m});
  }
  if(action==='retry' && req.method==='POST'){
   if(m.status!=='failed')return json({error:'Only failed jobs can be retried.'},409);m.status='queued';m.error=undefined;m.attempts=0;await put(m,'stage = :s AND revision = :r',{':s':{S:'failed'},':r':{N:String(m.revision)}});return json({match:m});
  }
  if(action==='edit' && req.method==='POST'){
   if(!['ready','needs_review','failed'].includes(m.status))return json({error:'Wait for processing to finish before editing.'},409);
   const b=await req.json() as any;if(b.music!==undefined && !musicChoices.has(b.music))return json({error:'Choose a listed instrumental or Random.'},400);if(b.revision!==m.revision)return json({error:'This match changed. Refresh before saving.'},409);
   if(!Array.isArray(b.events)||b.events.length>100)return json({error:'Too many highlights.'},400);
   const ids=new Set<string>();for(const e of b.events as Event[]){if(typeof e.id!=='string'||ids.has(e.id)||!Number.isFinite(e.start)||!Number.isFinite(e.end)||!Number.isFinite(e.time)||e.start<0||e.end>m.duration!||e.end<=e.start||e.end-e.start>90||e.time<e.start||e.time>e.end||typeof e.included!=='boolean')return json({error:'Each clip must be 1–90 seconds within the source, with its event inside its boundaries.'},400);ids.add(e.id);}
   m.events=b.events.map((e:Event)=>{const original=m.events.find(x=>x.id===e.id);return {...(original||{id:e.id,time:e.time,kind:'manual',manual:true,confidence:1,evidence:'Added by you'}),start:e.start,end:e.end,included:e.included};});m.length=[90,180,240].includes(b.length)?b.length:180;m.labels=!!b.labels;m.music=b.music||'random';m.revision++;m.status='queued';m.note='Your edits are saved. Waiting to render.';
   await put(m,'revision = :r AND (stage = :a OR stage = :b OR stage = :c)',{':r':{N:String(b.revision)},':a':{S:'ready'},':b':{S:'needs_review'},':c':{S:'failed'}});return json({match:m});
  }
  if(req.method==='DELETE' && !action){
   const revision=m.revision;m.revision++;m.status='discarded';
   // Invalidate any running worker before removing media; its lease writes require the old revision.
   await put(m,'revision = :r AND #s <> :d',{':r':{N:String(revision)},':d':{S:'discarded'}}, {'#s':'stage'});
   if(m.uploadId)try{await s3(m.key,`?uploadId=${encodeURIComponent(m.uploadId)}`,{method:'DELETE'});}catch{console.warn('Multipart cleanup deferred:',m.id);}
   return json({ok:true});
  }
  return json({error:'Not found.'},404);
 }catch(e){const msg=e instanceof Error?e.message:'Service unavailable.';console.error('Media API:',msg);return json({error:msg.includes('ConditionalCheckFailed')?'This match changed. Refresh and retry.':msg},msg==='Match not found.'?404:503);}
}
export const GET=handle,POST=handle,DELETE=handle;
