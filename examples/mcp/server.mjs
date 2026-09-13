import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { execFile } from 'node:child_process';
import { Transform } from 'node:stream';
import { isAbsolute } from 'node:path';
import { isUtf8 } from 'node:buffer';

const stage=process.env.PAYMENTS_MCP_STAGE;
const kujo=process.env.KUJO_BIN;
if (!stage || !kujo || !isAbsolute(stage) || !isAbsolute(kujo)) {
  process.stderr.write('Invalid payment frontend configuration\n'); process.exit(1);
}
const environment=Object.fromEntries(['PATH','PAYMENTS_CLIENT_ENDPOINT','PAYMENTS_CLIENT_TOKEN','PAYMENTS_LOCAL_FIXTURE','KUJO_ALLOW_PRIVATE_NETWORK_DESTINATIONS'].filter(k=>process.env[k]!==undefined).map(k=>[k,process.env[k]]));
function native(script,extra={}) {
  return new Promise((resolve,reject)=>{
    execFile(kujo,['run',script,'--interpreter'],{cwd:stage,env:{...environment,...extra},timeout:7000,maxBuffer:32768,killSignal:'SIGKILL',encoding:'utf8'},(error,stdout)=>{
      if(error) return reject(new Error('Payment client unavailable'));
      try { resolve(JSON.parse(stdout)); } catch { reject(new Error('Payment client unavailable')); }
    });
  });
}
const failure=()=>({content:[{type:'text',text:'Payment request unavailable; inspect the existing purchase before retrying.'}],isError:true});
// Bound each STDIO frame before SDK parsing. Reject fractional/exponent numeric
// wire tokens on tool calls before JavaScript can round them to integers.
let pending=Buffer.alloc(0);
const input=new Transform({transform(chunk,encoding,done){
  try {
    pending=Buffer.concat([pending,chunk]);
    let newline;
    while((newline=pending.indexOf(10))!==-1) {
      if(newline>8192) throw new Error();
      const line=pending.subarray(0,newline);pending=pending.subarray(newline+1);
      if(!isUtf8(line)) throw new Error();
      const raw=line.toString('utf8');
      let message;
      try { message=JSON.parse(raw); } catch { message=null; }
      if(message?.method==='tools/call') {
        for(const match of raw.matchAll(/"(?:\\.|[^"\\])*"|(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/g)) {
          if(match[1] && (/[.eE]/.test(match[1]) || !Number.isSafeInteger(Number(match[1])))) throw new Error();
        }
      }
      this.push(line);this.push('\n');
    }
    if(pending.length>8192) throw new Error();
    done();
  } catch { done(new Error('Invalid or oversized payment MCP frame')); }
}});
input.on('error',()=>{process.stderr.write('Invalid or oversized payment MCP frame\n');process.exit(1);});
let active=0;
try {
  const catalog=await native('project.kujo');
  if(!Array.isArray(catalog.tools)||catalog.tools.length!==2||catalog.tools[0].name!=='purchase_request'||catalog.tools[1].name!=='purchase_status') throw new Error();
  const server=new Server({name:'kujo-payments',version:'0.1.0'},{capabilities:{tools:{listChanged:false}}});
  server.setRequestHandler(ListToolsRequestSchema,async()=>({tools:catalog.tools}));
  server.setRequestHandler(CallToolRequestSchema,async(request)=>{
    if(active>=4) return failure();
    const operation=request.params.name==='purchase_request'?'request':request.params.name==='purchase_status'?'inspect':null;
    if(!operation) return failure();
    active++;
    try {
      const result=await native('call.kujo',{PAYMENTS_MCP_OPERATION:operation,PAYMENTS_MCP_INPUT:JSON.stringify(request.params.arguments??{})});
      if(result.ok!==true || !result.result || Object.keys(result).some(k=>!['ok','result'].includes(k))) return failure();
      return {content:[{type:'text',text:JSON.stringify(result.result)}],structuredContent:result.result};
    } catch { return failure(); } finally { active--; }
  });
  await server.connect(new StdioServerTransport(input,process.stdout,{maxBufferSize:16384}));
  process.stdin.pipe(input);
} catch {process.stderr.write('Payment MCP frontend unavailable\n');process.exit(1);}
