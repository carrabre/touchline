import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import { isPublicMatch, publicMatch } from '../lib/match-access.ts';
const base={id:'game',owner:'uploader',title:'Before',status:'ready',revision:4,events:[{id:'goal',included:true}],key:'source',reelKey:'reel-r4.mp4',renderMusic:{id:'titan',revision:4},length:180};
function route(overrides={},conflict=false){
 let saved;
 const match={...base,...overrides};
 const modules={
  '@/lib/aws':{owned:async(id,owner)=>{if(owner!==match.owner)throw new Error('Match not found.');return structuredClone(match);},put:async(m,c,v,n)=>{assert.match(c,/revision = :r AND #s = :s/);assert.equal(v[':r'].N,'4');assert.equal(n['#s'],'stage');if(conflict)throw new Error('ConditionalCheckFailed');saved=m;}},
  '@/lib/runtime-config':{runtimeConfig:()=>({MEDIA_ACCESS_KEY:'test-only',MEDIA_SECRET_KEY:'test-only'}),requestOwner:r=>r.headers.get('test-owner')},
  '@/lib/match-access':{isPublicMatch,publicMatch},'@/lib/soundtracks':{musicChoices:new Set()}
 };
 const source=ts.transpileModule(readFileSync(new URL('../app/api/[...path]/route.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const exports={};new Function('require','exports',source)(name=>modules[name],exports);
 return {call:(body,owner='uploader')=>exports.POST(new Request('https://test.example/api/matches/game/title',{method:'POST',headers:{origin:'https://test.example','content-type':'application/json','test-owner':owner},body:JSON.stringify(body)})),saved:()=>saved};
}
test('rename trims title, preserves clips and reel, and returns a safe public match',async()=>{
 const r=route();const response=await r.call({title:'  Sunday match  ',revision:4});assert.equal(response.status,200);const {match}=await response.json();
 assert.equal(match.title,'Sunday match');assert.equal(match.canEdit,true);assert.equal(match.owner,undefined);assert.equal(match.key,undefined);
 assert.equal(r.saved().revision,5);assert.equal(r.saved().status,'ready');assert.equal(r.saved().reelKey,base.reelKey);assert.deepEqual(r.saved().events,base.events);
});
test('title validation rejects blank, nontext, and overlong values',async()=>{
 for(const title of ['', '   ', 42, null, 'x'.repeat(101)]){const r=route();assert.equal((await r.call({title,revision:4})).status,400);assert.equal(r.saved(),undefined);}
 assert.equal((await route().call({title:'x'.repeat(100),revision:4})).status,200);
});
test('other viewers cannot rename shared games',async()=>{const r=route();assert.equal((await r.call({title:'Changed',revision:4},'visitor')).status,404);assert.equal(r.saved(),undefined);});
test('stale revisions and concurrent worker changes are rejected',async()=>{
 const r=route();assert.equal((await r.call({title:'Changed',revision:3})).status,409);assert.equal(r.saved(),undefined);
 assert.equal((await route({},true).call({title:'Changed',revision:4})).status,409);
});
test('rename waits for uploads and processing to finish',async()=>{
 for(const status of ['uploading','queued','ingestion','analysis','selection','rendering']){const r=route({status});assert.equal((await r.call({title:'Changed',revision:4})).status,409);assert.equal(r.saved(),undefined);}
});
test('review and failed games can also be renamed',async()=>{for(const status of ['needs_review','failed'])assert.equal((await route({status}).call({title:'Changed',revision:4})).status,200);});
