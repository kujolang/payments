"""Independent oracle for the flat identity profiles actually used by Payments.

This does not model or repair Ability's legacy nested serializer.
"""
import argparse,hashlib,json
from pathlib import Path

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def framed(parts):
    return hashlib.sha256(''.join(f'{len(v.encode())}:{v}' for v in parts).encode()).hexdigest()
def vectors():
    result=[]
    principals=[{'type':'user','id':'same-user','tenant_id':'tenant-a'},
                {'type':'user','id':'same-user','tenant_id':'tenant-b'},
                {'type':'service','id':'same-user','tenant_id':'tenant-a'},
                {'type':'user','id':'different-user','tenant_id':'tenant-a'},
                {'type':'T'*64,'id':'I'*128,'tenant_id':'N'*128},
                {'type':'user:delegated','id':'payer._-:1','tenant_id':'tenant._-:2'}]
    keys=['same-key','quote"slash\\newline\n', '日本語/clé', 'k'*128, 'prefix\tkey', '0:1:two']
    for index in range(36):
        principal=principals[index%len(principals)];key=keys[index//len(principals)]
        scope=framed(['kujo.payment-principal/v1',principal['type'],principal['id'],principal['tenant_id']])
        key_digest=digest({'tenant_id':principal['tenant_id'],'principal_type':principal['type'],'principal_id':principal['id'],'idempotency_key':key})
        row={'execution_id':'exec:'+str(index),'snapshot_digest':hashlib.sha256(('snapshot:'+str(index)).encode()).hexdigest()}
        approval=digest({'ability_id':'kujo.payments.execution.execute','ability_version':'1.0.0','definition_digest':'00f65a051d700d106a5546c359f67b43e8ba04c560adf6bb8938e84d9abfdf1d','input_digest':digest(row),'principal_digest':digest(principal),'tenant_id':principal['tenant_id'],'invocation_id':'execute:'+row['execution_id']})
        result.append({'principal':principal,'key':key,'scope':scope,'row':row,'approval_binding':approval,'request_key_digest':key_digest,'cancel_key_digest':framed(['kujo.payment-cancel-key/v1',scope,key_digest]),'purchase_ref':'scope-purchase-'+str(index)})
    assert len({v['request_key_digest'] for v in result})==len(result)
    assert len({v['approval_binding'] for v in result})==len(result)
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    data=vectors();Path(args.output).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');print(f'{len(data)} independent flat identity vectors generated')
