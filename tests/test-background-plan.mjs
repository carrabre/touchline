import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import { isPublicMatch, publicMatch } from '../lib/match-access.ts';
const CHUNK=16*1024**2;
function handler(overrides={}){
 const m={id:'job',owner:'native',status:'uploading',backgroundUpload:true,recording:false,size:CHUNK*2+1,uploadId:'upload-id',key:'matches/native/job/source',...overrides};let signatures=[];
 const modules={
  '@/lib/aws':{owned:async(id,owner)=>{if(owner!==m.owner)throw new Error('Match not found.');return m;},parts:async()=>[{number:2,size:CHUNK}],signed:async(key,method,query,expires)=>{signatures.push({key,method,query,expires});return 'https://storage.example/upload';}},
  '@/lib/runtime-config':{runtimeConfig:()=>({MEDIA_ACCESS_KEY:'test-only',MEDIA_SECRET_KEY:'test-only'}),requestOwner:r=>r.headers.get('test-owner')},
  '@/lib/match-access':{isPublicMatch,publicMatch},'@/lib/soundtracks':{musicChoices:new Set()}
 };
 const source=ts.transpileModule(readFileSync(new URL('../app/api/[...path]/route.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const exports={};new Function('require','exports',source)(name=>modules[name],exports);
 return {call:(owner='native')=>exports.POST(new Request('https://test.example/api/matches/job/background-plan',{method:'POST',headers:{'test-owner':owner,origin:'https://test.example'},body:'{}'})),signatures:()=>signatures};
}
test('native plan schedules only missing parts with scoped seven-day PUT URLs',async()=>{
 const h=handler();const r=await h.call();assert.equal(r.status,200);const body=await r.json();assert.deepEqual(body.parts.map(p=>p.number),[1,3]);assert.equal(body.chunkSize,CHUNK);
 for(const s of h.signatures()){assert.equal(s.method,'PUT');assert.equal(s.expires,604800);assert.equal(s.key,'matches/native/job/source');assert.match(s.query,/uploadId=upload-id/);}
});
test('public viewers cannot obtain native upload URLs',async()=>{const h=handler();assert.equal((await h.call('stranger')).status,404);assert.equal(h.signatures().length,0);});
test('completed, browser, and recording jobs cannot receive a native plan',async()=>{for(const overrides of [{status:'ready'},{backgroundUpload:false},{recording:true}]){const h=handler(overrides);assert.equal((await h.call()).status,409);assert.equal(h.signatures().length,0);}});
