"""Repeated synthetic Link lifecycle measurements; no real provider latency claim."""
import json,math,os,statistics,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCENARIOS=['success','lost_charge','changed_challenge','unverified_2xx']
PHASES=['prepare_and_authorize','authorization_poll','operator_review_and_grant','submit','followup']
MARKER='Link five-method SPI through worker and Ability: native approval, operator grant, private credential, one-shot submission and confirmed reconciliation passed'
SAMPLES=8
samples={s:[] for s in SCENARIOS};process_times=[]
with tempfile.TemporaryDirectory(prefix='payments-link-performance-') as directory:
    for index in range(SAMPLES):
        started=time.perf_counter()
        result=subprocess.run([os.environ['KUJO_BIN'],'run','tests/link_provider.kujo','--interpreter'],cwd=ROOT,
                              env={**os.environ,'PAYMENTS_MEASURE_LINK':'1','PAYMENTS_TEST_DB':str(Path(directory)/str(index))},
                              capture_output=True,text=True,timeout=30)
        process_times.append((time.perf_counter()-started)*1000)
        assert result.returncode==0,'Link performance fixture failed'
        assert len((result.stdout+result.stderr).encode())<=32768,'fixture output budget exceeded'
        assert 'SENTINEL' not in result.stdout+result.stderr,'secret in fixture output'
        lines=result.stdout.splitlines();assert lines[-1]==MARKER
        records=[json.loads(line.removeprefix('Link measurement: ')) for line in lines if line.startswith('Link measurement: ')]
        assert len(records)==4 and {r['scenario'] for r in records}==set(SCENARIOS)
        for record in records:
            assert set(record)=={'schema','scenario','phase_ms','calls','summary_bytes','first_status','followup_status'}
            assert record['schema']=='kujo.payment-fixture-measurement/v1' and set(record['phase_ms'])==set(PHASES)
            assert all(type(v) in [int,float] and math.isfinite(v) and v>=0 for v in record['phase_ms'].values())
            assert set(record['summary_bytes'])=={'pending','first','followup'}
            assert all(type(v) is int and 0<v<=512 for v in record['summary_bytes'].values()),'compact summary budget'
            calls=record['calls'];assert set(calls)=={'POST','GET','probe','pay','credential'}
            assert all(type(v) is int and v>=0 for v in calls.values())
            assert calls['POST']==1 and calls['pay']==(0 if record['scenario']=='changed_challenge' else 1)
            assert calls['credential']==(0 if record['scenario']=='changed_challenge' else 1)
            assert record['first_status']==('succeeded' if record['scenario']=='success' else 'reconciliation_required')
            assert record['followup_status']==('succeeded' if record['scenario'] in ['success','lost_charge'] else 'reconciliation_required')
            samples[record['scenario']].append(record)

def distribution(values):
    ordered=sorted(values)
    return {'samples':len(values),'min_ms':min(values),'median_ms':statistics.median(values),'p95_ms':ordered[math.ceil(.95*len(values))-1],'max_ms':max(values)}

summary={}
for scenario,records in samples.items():
    assert len(records)==SAMPLES
    assert all(r['calls']==records[0]['calls'] and r['summary_bytes']==records[0]['summary_bytes'] for r in records),'nondeterministic fixture costs'
    summary[scenario]={'phase_ms':{p:distribution([r['phase_ms'][p] for r in records]) for p in PHASES},'calls_per_flow':records[0]['calls'],'summary_bytes':records[0]['summary_bytes']}
print(MARKER)
print('Link lifecycle measurements: '+json.dumps({'schema':'kujo.payment-fixture-performance/v1','scope':'synthetic_in_process_provider_callbacks','native_process_count':SAMPLES,'flows_per_process':4,'process_ms':distribution(process_times),'scenarios':summary},sort_keys=True))
