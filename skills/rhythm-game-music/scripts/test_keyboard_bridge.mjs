import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {startBridge} from '../assets/portable-player/keyboard-audio-bridge.mjs';
test('keyboard bridge accepts the actual local performance origin and rejects other pages',async()=>{
 const origin='http://127.0.0.1:45678';
 const app=startBridge({httpPort:0,udpPort:0,pageOrigin:origin});
 try{
  await Promise.all([once(app.server,'listening'),once(app.udp,'listening')]);
  const url=`http://127.0.0.1:${app.server.address().port}/status`;
  const allowed=await fetch(url,{headers:{Origin:origin}});assert.equal(allowed.status,200);assert.equal(allowed.headers.get('Access-Control-Allow-Origin'),origin);
  assert.equal((await allowed.json()).connected,false);
  assert.equal((await fetch(url,{headers:{Origin:'https://example.org'}})).status,403);
  assert.equal((await fetch(url,{headers:{Origin:'http://127.0.0.1:4188'}})).status,403);
 }finally{app.close();}
});
test('remote and malformed page origins are rejected',()=>{
 for(const pageOrigin of ['https://example.org','http://192.168.1.1:4192','http://127.0.0.1:4192/'])assert.throws(()=>startBridge({pageOrigin}));
});
