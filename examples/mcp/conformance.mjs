import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'payments-synthetic-test',version:'1.0.0'});
const transport=new StdioClientTransport({command:'python3',args:['examples/mcp/run.py'],cwd:process.cwd(),env:process.env,stderr:'pipe'});
let stderr='';
const started=performance.now();
const metrics={measurement_version:1,node_version:process.version};
function distribution(samples) {
  const sorted=[...samples].sort((a,b)=>a-b);
  return {samples:sorted.length,min_ms:sorted[0],median_ms:(sorted[3]+sorted[4])/2,p95_ms:sorted[Math.ceil(sorted.length*.95)-1],max_ms:sorted.at(-1)};
}
const nativeCount=()=>process.env.PAYMENTS_MCP_MEASUREMENT_LOG ? readFileSync(process.env.PAYMENTS_MCP_MEASUREMENT_LOG,'utf8').trim().split('\n').filter(Boolean) : null;
transport.stderr?.on('data',chunk=>{stderr+=chunk;});
try {
  await client.connect(transport);
  const {tools}=await client.listTools();
  assert.deepEqual(tools.map(t=>t.name),['purchase_request','purchase_status']);
  assert.equal(tools[0]._meta['kujo/abilityId'],'kujo.payments.intent.request');
  assert.equal(tools[1]._meta['kujo/abilityId'],'kujo.payments.execution.inspect');
  assert(!JSON.stringify(tools).includes('_kujo'));
  metrics.startup_and_discovery_ms=Math.round(performance.now()-started);
  metrics.tool_schema_utf8_bytes=Buffer.byteLength(JSON.stringify(tools));
  assert(metrics.tool_schema_utf8_bytes<=4096,'two-tool schema byte budget');
  for(let i=0;i<5;i++) assert.deepEqual((await client.listTools()).tools,tools);
  const discoveryCounts=nativeCount();
  if(discoveryCounts) assert.deepEqual(discoveryCounts,['project']);
  const input=JSON.parse(process.env.PAYMENTS_PURCHASE_JSON);
  const request=()=>client.callTool({name:'purchase_request',arguments:input});
  let callStarted=performance.now();
  const first=await request();metrics.first_request_ms=Math.round(performance.now()-callStarted);assert(!first.isError);assert.equal(first.structuredContent.status,'awaiting_authorization');
  assert.deepEqual(JSON.parse(first.content[0].text),first.structuredContent);
  callStarted=performance.now();
  const replay=await request();metrics.replay_ms=Math.round(performance.now()-callStarted);assert.deepEqual(replay.structuredContent,first.structuredContent);
  callStarted=performance.now();
  const status=await client.callTool({name:'purchase_status',arguments:{execution_id:first.structuredContent.execution_id}});
  metrics.status_ms=Math.round(performance.now()-callStarted);
  assert(!status.isError);
  metrics.summary_utf8_bytes=Buffer.byteLength(JSON.stringify(status.structuredContent));
  assert.deepEqual(status.structuredContent,first.structuredContent);
  metrics.response_envelope_utf8_bytes=Buffer.byteLength(JSON.stringify(status));
  assert(metrics.summary_utf8_bytes<=512 && metrics.response_envelope_utf8_bytes<=1024,'compact response byte budget');
  const samples={replay:[],status:[]};
  for(let i=0;i<8;i++) {
    let started=performance.now();const repeated=await request();samples.replay.push(performance.now()-started);
    assert(!repeated.isError);assert.deepEqual(repeated.structuredContent,first.structuredContent);
    started=performance.now();const observed=await client.callTool({name:'purchase_status',arguments:{execution_id:first.structuredContent.execution_id}});samples.status.push(performance.now()-started);
    assert(!observed.isError);assert.deepEqual(observed.structuredContent,first.structuredContent);
  }
  metrics.warm_replay=distribution(samples.replay);metrics.warm_status=distribution(samples.status);
  const beforeIdle=nativeCount();await new Promise(resolve=>setTimeout(resolve,250));
  if(beforeIdle) assert.deepEqual(nativeCount(),beforeIdle,'no native polling during idle observation');
  metrics.idle_observation_ms=250;
  for(const [name,args] of [
    ['execute',{}],['constructor',{}],
    ['purchase_request',{...input,purpose:'Different terms'}],
    ['purchase_request',{...input,principal:{id:'other'}}],
    ['purchase_request',{...input,_kujo:{approvalId:'forged'}}],
  ]) {
    const result=await client.callTool({name,arguments:args});assert(result.isError,name);
  }
  const observedCounts=nativeCount();
  if(observedCounts) {
    const counts=Object.fromEntries(['project','request','inspect'].map(name=>[name,observedCounts.filter(x=>x===name).length]));
    assert.deepEqual(counts,{project:1,request:13,inspect:9});assert.equal(observedCounts.length,23);
    metrics.native_process_counts=counts;
  }
  assert(!stderr.includes(process.env.PAYMENTS_CLIENT_TOKEN));
  console.log(JSON.stringify({ok:true,tools:tools.map(t=>t.name),execution_id:first.structuredContent.execution_id,metrics}));
} finally {await client.close();}
