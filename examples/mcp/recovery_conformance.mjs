import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'payment-recovery-test',version:'1.0.0'});
const transport=new StdioClientTransport({command:'python3',args:['examples/mcp/run.py'],cwd:process.cwd(),env:process.env,stderr:'pipe'});
let stderr='';transport.stderr?.on('data',chunk=>{stderr+=chunk;});
try {
  await client.connect(transport);
  const {tools}=await client.listTools();assert.deepEqual(tools.map(t=>t.name),['purchase_request','purchase_status']);
  const request=await client.callTool({name:'purchase_request',arguments:JSON.parse(process.env.PAYMENTS_PURCHASE_JSON)});
  assert.equal(request.isError,true);
  if(process.env.PAYMENTS_EXPECT_OBSERVATION==='true') {
    assert.equal(request.structuredContent.execution_id,'exec_recovery');
    const fresh=await client.callTool({name:'purchase_status',arguments:{execution_id:'exec_recovery'}});
    if(process.env.PAYMENTS_WRONG_STATUS==='true') { assert.equal(fresh.isError,true);assert.equal(fresh.structuredContent,undefined); }
    else { assert(!fresh.isError);assert.equal(fresh.structuredContent.status,'awaiting_authorization'); }
  } else { assert.equal(request.structuredContent,undefined); }
  assert(!JSON.stringify(request).includes(process.env.PAYMENTS_PRIVATE_SENTINEL));
  assert(!stderr.includes(process.env.PAYMENTS_CLIENT_TOKEN));
  console.log(JSON.stringify({ok:true,request_is_error:request.isError,observation_retained:!!request.structuredContent}));
} finally {await client.close();}
