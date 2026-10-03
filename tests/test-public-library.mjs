import assert from 'node:assert/strict';
import { test } from 'node:test';
import { isPublicMatch, publicMatch } from '../lib/match-access.ts';
const match = {id:'a-game',owner:'uploader',key:'recording-key',uploadId:'multipart-id',metrics:{internal:'diagnostics'},status:'ready',title:'Sunday match',events:[],revision:0};
test('games and in-progress uploads are visible; discarded jobs and internal fixtures are hidden',()=>{
  assert.equal(isPublicMatch(match),true);
  assert.equal(isPublicMatch({...match,status:'uploading'}),true);
  assert.equal(isPublicMatch({...match,status:'discarded'}),false);
  assert.equal(isPublicMatch({...match,id:'validation-internal'}),false);
});
test('all visitors can see a game, with editing rights only for its uploader',()=>{
  const uploader=publicMatch(match,'uploader'),visitor=publicMatch(match,'another-browser');
  assert.equal(uploader.title,visitor.title);
  assert.equal(uploader.canEdit,true);
  assert.equal(visitor.canEdit,false);
  for(const field of ['owner','key','uploadId','metrics'])assert.equal(field in visitor,false);
});
