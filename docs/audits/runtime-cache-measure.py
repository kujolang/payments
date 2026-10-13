import hashlib,json,pathlib,shutil,subprocess,sys,tempfile
with tempfile.TemporaryDirectory() as directory:
 root=pathlib.Path(directory);(root/'scripts/deployment').mkdir(parents=True);(root/'deployment/.runtime').mkdir(parents=True)
 script=root/'scripts/deployment/fetch_runtime.py';shutil.copyfile(sys.argv[1],script)
 binary=b'x'*(8*1024*1024);(root/'deployment/.runtime/kujo').write_bytes(binary)
 (root/'deployment/runtime.lock.json').write_text(json.dumps({'binary_sha256':hashlib.sha256(binary).hexdigest()}))
 code='''import hashlib,io,json,tarfile,urllib.request,os,tempfile,pathlib,runpy,sys,time,tracemalloc
tracemalloc.start();start=time.perf_counter()
try:runpy.run_path(sys.argv[1])
except SystemExit as e:
 if e.code not in (None,0):raise
print(json.dumps({'cache_bytes':8388608,'peak_python_bytes':tracemalloc.get_traced_memory()[1],'elapsed_ms':(time.perf_counter()-start)*1000}))'''
 result=subprocess.run([sys.executable,'-c',code,str(script)],check=True,capture_output=True,text=True)
 print(result.stdout.splitlines()[-1])
