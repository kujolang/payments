"""Independent test oracle, not a production Payments implementation."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def scalar(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    return str(v)

def optional(v):
    return ['0'] if v is None else ['1', scalar(v)]

def counted(v):
    return [str(len(v)), *v]

def nullable_set(v):
    return ['0'] if v is None else ['1', *counted(sorted(v))]

def parts(kind, v):
    if kind == 'intent':
        p, a = v['principal'], v['amount']
        out = ['kujo.payment-intent-binding/v1', v['intent_id'], v['purchase_ref'], p['type'], p['id'], p['tenant_id'], v['kind'], v['payee_ref'], a['mode'], str(a['minor']), a['currency'], v['purpose'], str(v['expires_at_ms']), v['payment_profile'], v['correlation_id']]
        out += optional(v.get('shipping_profile')) + optional(v.get('provider_preference'))
        items = v.get('items', [])
        out += [str(len(items))]
        for item in items:
            out += [item['sku'], str(item['quantity'])]
        return out
    if kind == 'snapshot':
        p, payee, a = v['principal'], v['payee'], v['charge']
        r, profile, provider = v['request_binding'], v['payment_profile'], v['provider']
        out = ['kujo.payment-snapshot-binding/v1', p['type'], p['id'], p['tenant_id'], v['execution_id'], v['intent_digest'], payee['id'], payee['registry_version'], payee['display_name'], payee['origin'], str(a['minor']), a['currency'], v['currency_table_version'], r['route_id'], r['route_version'], r['resource_ref'], r['terms_digest'], profile['alias'], profile['version']]
        shipping = v['shipping_profile']
        out += ['0'] if shipping is None else ['1', shipping['alias'], shipping['version']]
        return out + [provider['id'], provider['adapter_version'], provider['account_ref'], v['execution_class'], v['capabilities_digest'], str(v['expires_at_ms'])]
    c, r, o = v['constraints'], v['replay_protection'], v['observation_support']
    out = ['kujo.payment-capabilities-binding/v1', v['schema'], v['provider_id'], v['adapter_version']]
    out += counted(sorted(v['actions'])) + counted(sorted(v['execution_classes']))
    out += [str(v['observed_at_ms']), str(v['valid_until_ms']), scalar(o['authorization']), scalar(o['execution']), r['strategy']]
    out += optional(r['retention_ms']) + nullable_set(c['currencies']) + nullable_set(c['regions'])
    out += [str(len(c['amount_limits']))]
    for limit in sorted(c['amount_limits'], key=lambda x: x['currency']):
        out += [limit['currency']] + optional(limit['minimum_minor']) + optional(limit['maximum_minor'])
    return out + optional(c['authorization_required']) + optional(c['credential_expires_at_ms']) + optional(c['available'])

def digest(kind, value):
    fields = parts(kind, value)
    encoded = ''.join(f'{len(s.encode("utf-8"))}:{s}' for s in fields)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()

def leaves(value, path=()):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from leaves(v, (*path, k))
    elif isinstance(value, list):
        for k, v in enumerate(value):
            yield from leaves(v, (*path, k))
    elif value is not None:
        yield path, value

def generate():
    examples = json.loads((ROOT/'tests/fixtures/domain.json').read_text())
    examples['intent'].update(items=[{'sku': 'sku-1', 'quantity': 2}], shipping_profile='home', provider_preference='fixture')
    examples['snapshot']['shipping_profile'] = {'alias': 'home', 'version': 'v1'}
    vectors = []
    for kind in ['intent', 'snapshot', 'capabilities']:
        v = examples[kind]
        base = digest(kind, v)
        vectors.append(dict(kind=kind, name='base', value=v, sha256=base))
        for path, old in leaves(v):
            if kind == 'intent' and path == ('schema',):
                continue  # Fixed schema is validated before binding.
            edited = copy.deepcopy(v)
            parent = edited
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = not old if isinstance(old, bool) else old + 1 if isinstance(old, int) else old + '-changed'
            result = digest(kind, edited)
            assert result != base, (kind, path)
            vectors.append(dict(kind=kind, name='.'.join(map(str, path)), value=edited, sha256=result))
    for purpose in ['é', 'e\u0301', 'a:b|c', '']:
        v = copy.deepcopy(examples['intent'])
        v['purpose'] = purpose
        vectors.append(dict(kind='intent', name='utf8', value=v, sha256=digest('intent', v)))
    return json.dumps(vectors, ensure_ascii=False, indent=2)+'\n'

if __name__ == '__main__':
    import sys
    target = ROOT/'tests/fixtures/binding-vectors.json'
    result = generate()
    if '--check' in sys.argv:
        assert target.read_text() == result, 'Binding vectors differ from independent oracle'
    else:
        target.write_text(result)
