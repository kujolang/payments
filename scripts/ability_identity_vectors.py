"""Independent Python canonical-JSON identity and definition mutation vectors."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
pins=json.loads((ROOT/'contracts/ability-identities.json').read_text())
source=(ROOT/'src/identity/canonical.kujo').read_text()
compiled=json.loads(re.search(r'pins := (\{[^\n]+\})',source)[1])
assert pins==compiled,'Compiled identity pins differ from reviewed inventory'
cases=[]
def leaves(value,path=()):
    if isinstance(value,dict):
        for k,v in value.items(): yield from leaves(v,path+(k,))
    elif isinstance(value,list):
        for k,v in enumerate(value): yield from leaves(v,path+(k,))
    else: yield path,value
for operation,pin in pins.items():
    definition=json.loads((ROOT/f'contracts/abilities/{operation}.json').read_text())
    canonical=json.dumps(definition,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    assert hashlib.sha256(canonical.encode()).hexdigest()==pin['digest']
    cases.append({'operation':operation,'definition':definition,'matches':True})
    for path,value in leaves(definition):
        changed=json.loads(canonical);parent=changed
        for k in path[:-1]:parent=parent[k]
        parent[path[-1]]=not value if isinstance(value,bool) else value+1 if isinstance(value,int) else str(value)+'-mutated'
        cases.append({'operation':operation,'definition':changed,'matches':False})
    changed=json.loads(canonical);changed['metadata']={'unreviewed':True}
    cases.append({'operation':operation,'definition':changed,'matches':False})
    cases.append({'operation':'unknown','definition':definition,'matches':False})
output=json.dumps(cases,separators=(',',':'),ensure_ascii=False)+'\n'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();args.output.write_text(output)
print(f'{len(cases)} independent definition identity vectors checked')
