import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import ts from 'typescript';
import { isPublicMatch, publicMatch } from '../lib/match-access.ts';
const require=createRequire(import.meta.url);
function route(match,{storageFails=false,conflict=false}={}) {
  let saved,condition;
  const aws={
    owned:async(id,owner)=>{if(id!==match.id||owner!==match.owner)throw new Error('Match not found.');return structuredClone(match);},
    put:async(m,c,v,n)=>{condition={c,v,n};if(conflict)throw new Error('ConditionalCheckFailed');saved=m;},
    s3:async()=>{if(storageFails)throw new Error('Storage offline');},
  };
  const modules={
    '@/lib/aws':aws,
    '@/lib/runtime-config':{runtimeConfig:()=>({MEDIA_ACCESS_KEY:'test-only',MEDIA_SECRET_KEY:'test-only'}),requestOwner:r=>r.headers.get('test-owner')},
    '@/lib/match-access':{isPublicMatch,publicMatch},
    '@/lib/soundtracks':{musicChoices:new Set()},
  };
  const source=ts.transpileModule(readFileSync(new URL('../app/api/[...path]/route.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const exports={};new Function('require','exports',source)(name=>modules[name]??require(name),exports);
  return {call:owner=>exports.DELETE(new Request(`https://test.example/api/matches/${match.id}`,{method:'DELETE',headers:{'test-owner':owner,origin:'https://test.example'}})),saved:()=>saved,condition:()=>condition};
}
for(const status of ['uploading','queued','ingestion','analysis','selection','rendering','ready','needs_review','failed']) {
  test(`uploader can delete ${status} and invalidate the worker revision`,async()=>{
    const r=route({id:'game',owner:'uploader',status,revision:7,uploadId:status==='uploading'?'pending':undefined});
    assert.equal((await r.call('uploader')).status,200);
    assert.equal(r.saved().status,'discarded');assert.equal(r.saved().revision,8);
    assert.equal(r.condition().v[':r'].N,'7');assert.match(r.condition().c,/revision = :r/);
  });
}
test('another viewer cannot delete shared media',async()=>{
  const r=route({id:'game',owner:'uploader',status:'ready',revision:0});
  assert.equal((await r.call('stranger')).status,404);assert.equal(r.saved(),undefined);
});
test('multipart cleanup failure cannot bring a deleted upload back',async()=>{
  const r=route({id:'game',owner:'uploader',status:'uploading',revision:0,uploadId:'pending'},{storageFails:true});
  assert.equal((await r.call('uploader')).status,200);assert.equal(r.saved().status,'discarded');
});
test('concurrent updates do not get silently overwritten by deletion',async()=>{
  const r=route({id:'game',owner:'uploader',status:'rendering',revision:0},{conflict:true});
  const response=await r.call('uploader');assert.notEqual(response.status,200);assert.equal(r.saved(),undefined);
});
