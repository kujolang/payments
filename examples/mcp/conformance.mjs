import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'payments-synthetic-test',version:'1.0.0'});
const transport=new StdioClientTransport({command:'python3',args:['examples/mcp/run.py'],cwd:process.cwd(),env:process.env,stderr:'pipe'});
let stderr='';
const started=performance.now();
const metrics={};
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
  for(const [name,args] of [
    ['execute',{}],['constructor',{}],
    ['purchase_request',{...input,purpose:'Different terms'}],
    ['purchase_request',{...input,principal:{id:'other'}}],
    ['purchase_request',{...input,_kujo:{approvalId:'forged'}}],
  ]) {
    const result=await client.callTool({name,arguments:args});assert(result.isError,name);
  }
  assert(!stderr.includes(process.env.PAYMENTS_CLIENT_TOKEN));
  console.log(JSON.stringify({ok:true,tools:tools.map(t=>t.name),execution_id:first.structuredContent.execution_id,metrics}));
} finally {await client.close();}
