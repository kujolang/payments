"""MCP launcher must reap its isolated Node/native process group on termination."""
import errno
import json
import os
from pathlib import Path
import select
import subprocess
import time
ROOT=Path(__file__).resolve().parents[2]
process=subprocess.Popen(['python3','examples/mcp/run.py'],cwd=ROOT,env=os.environ,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    message={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'cleanup-test','version':'1.0.0'}}}
    process.stdin.write(json.dumps(message)+'\n');process.stdin.flush()
    assert select.select([process.stdout],[],[],10)[0],'initialize timeout'
    response=json.loads(process.stdout.readline());assert response['result']['serverInfo']['name']=='kujo-payments'
    rows=subprocess.check_output(['ps','-axo','pid=,ppid='],text=True)
    children=[int(parts[0]) for line in rows.splitlines() if len(parts:=line.split())==2 and int(parts[1])==process.pid]
    assert len(children)==1,children
    group=os.getpgid(children[0]);assert group==children[0]
    process.terminate();process.wait(timeout=5)
    deadline=time.monotonic()+5
    while True:
        try: os.killpg(group,0)
        except OSError as error:
            assert error.errno==errno.ESRCH;break
        assert time.monotonic()<deadline,'orphaned MCP process group'
        time.sleep(.02)
    print('MCP launcher: initialized SDK transport and terminated process group without orphaned children')
finally:
    if process.poll() is None: process.terminate();process.wait(timeout=5)
    process.stdin.close();process.stdout.close();process.stderr.close()
