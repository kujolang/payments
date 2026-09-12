#!/usr/bin/env python3
"""Independent fixture oracle for the supported mppx 0.8.15 Stripe charge subset."""
import base64,copy,datetime,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def b64(x):return base64.urlsafe_b64encode(x.encode()).decode().rstrip('=')
request={'amount':'5500','currency':'usd','methodDetails':{'networkId':'network_1','paymentMethodTypes':['card']}}
fields={'id':'challenge_1','realm':'merchant.example','method':'stripe','intent':'charge','request':b64(canon(request)),'expires':'2026-09-13T00:00:00.000Z'}
expected={'realm':'merchant.example','charge':{'minor':5500,'currency':'USD'},'network_id':'network_1','payment_method_types':['card'],'recipient':None,'body_digest':None}
def header(f):return 'Payment '+', '.join(k+'='+json.dumps(v,ensure_ascii=True) for k,v in f.items())
cases=[]
def add(name,f,valid=False,raw=None,now_ms=0):
 c={'name':name,'header':header(f) if raw is None else raw,'valid':valid,'now_ms':now_ms}
 if valid:
  payload={'spt':'SENTINEL_SPT'}
  decoded=json.loads(base64.urlsafe_b64decode(f['request']+'='*((-len(f['request']))%4)))
  if 'externalId' in decoded:payload['externalId']=decoded['externalId']
  c.update(expires_at_ms=int(datetime.datetime.fromisoformat(f['expires'].replace('Z','+00:00')).timestamp()*1000),digest=hashlib.sha256(canon(f).encode()).hexdigest(),credential='Payment '+b64(canon({'challenge':f,'payload':payload})))
 cases.append(c)
add('canonical',fields,True)
f={**fields,'description':'A, B and "quoted" item','opaque':b64('{"order":"one"}')};add('opaque_and_quoted',f,True)
r={**request,'description':'Coffee ☕','externalId':'order_1'};add('unicode_in_request',{**fields,'request':b64(canon(r))},True)
r=copy.deepcopy(request);r['methodDetails']['metadata']={'order':'one'};add('metadata',{**fields,'request':b64(canon(r))},True)
for key,value in [('method','tempo'),('intent','session'),('realm','evil.example'),('id','../../id'),('expires','2026-02-30T00:00:00.000Z'),('expires','2026-09-13T24:00:00.000Z'),('expires','2026-09-13T00:00:00Z'),('expires','2026-09-13T00:00:00.000+00:00'),('request','@@@@'),('opaque','not base64'),('digest','sha-256=unrequested')]:
 add('field_'+key+'_'+value,{**fields,key:value})
for key in ('id','realm','method','intent','request','expires'):
 f=dict(fields);del f[key];add('missing_'+key,f)
for value in ('5500.0','5.5e3','05500','+5500','-5500','0','9007199254740992',5500,5500.0,True):
 add('amount_'+type(value).__name__+'_'+str(value),{**fields,'request':b64(canon({**request,'amount':value}))})
for key,value in [('currency','eur'),('currency','USD'),('recipient','acct_other'),('unknown','value'),('externalId',{'bad':'shape'})]:
 add('request_'+key,{**fields,'request':b64(canon({**request,key:value}))})
for key,value in [('networkId','other'),('paymentMethodTypes',['crypto']),('paymentMethodTypes',[]),('metadata',{'x':False}),('unrecognized','x')]:
 r=copy.deepcopy(request);r['methodDetails'][key]=value;add('details_'+key,{**fields,'request':b64(canon(r))})
for name,raw in [('duplicate','{"amount":"1","amount":"5500","currency":"usd","methodDetails":{"networkId":"network_1","paymentMethodTypes":["card"]}}'),('spaces',json.dumps(request)),('unsorted','{"currency":"usd","amount":"5500","methodDetails":{"networkId":"network_1","paymentMethodTypes":["card"]}}')]:
 add(name,{**fields,'request':b64(raw)})
for name,raw in [('duplicate_header',header(fields)+', id="other"'),('two_challenges',header(fields)+', '+header(fields)),('trailing_comma',header(fields)+','),('unquoted',header(fields).replace('method="stripe"','method=stripe')),('newline',header(fields)+'\n'),('unknown_param',header(fields)+', extra="x"'),('basic','Basic abc'),('huge','Payment '+'x'*20001),('bad_escape',header(fields)+', description="bad\\n"')]:
 add(name,fields,raw=raw)
add('expired',fields,now_ms=1789257600000)
add('padding',{**fields,'request':fields['request']+'='})
value=json.dumps({'source':'mppx 0.8.15 Credential.serialize and PaymentRequest.serialize; independent Python oracle for the supported string-only subset','expected':expected,'cases':cases},indent=2,ensure_ascii=False)+'\n'
path=ROOT/'tests/fixtures/mpp.json'
if '--check' in sys.argv:assert path.read_text()==value,'MPP fixture drift'
else:path.write_text(value)
print('MPP vectors:',len(cases))
