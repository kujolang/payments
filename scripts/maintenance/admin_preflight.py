"""Fail-closed private-file prerequisite for local operator/control launchers.

The administrator must control path ancestors and the runtime. These checks do
not authenticate a user or protect against a same-principal/host attacker.
"""
import json
import os
from pathlib import Path
import sys
from verify_recovery import private_file, unique_object


def validate(kind):
    names = {'operator': ('PAYMENTS_OPERATOR_CONFIG', 'kujo.payment-operator/v1'),
             'control': ('PAYMENTS_CONTROL_CONFIG', 'kujo.payment-control/v1')}
    variable, schema = names[kind]
    runtime = Path(os.environ['KUJO_BIN'])
    if not runtime.is_absolute() or not runtime.is_file() or not os.access(runtime, os.X_OK):
        raise ValueError('runtime')
    config = Path(os.environ[variable])
    if not config.is_absolute():
        raise ValueError('absolute config required')
    private_file(config.parent, directory=True)
    before = private_file(config)
    if before[2] > 65536:
        raise ValueError('config limit')
    # Private parent plus O_NOFOLLOW closes the final-component symlink case;
    # trusted custody of ancestors and same-UID processes remains required.
    fd = os.open(config, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (info.st_dev, info.st_ino) != before[:2]:
            raise ValueError('config changed')
        raw = stream.read(65537)
    if len(raw) > 65536 or private_file(config) != before:
        raise ValueError('config changed')
    value = json.loads(raw, object_pairs_hook=unique_object)
    if type(value) is not dict or value.get('schema') != schema or type(value.get('database')) is not str:
        raise ValueError('config')
    database = Path(value['database'])
    if not database.is_absolute():
        raise ValueError('absolute journal required')
    private_file(database.parent, directory=True)
    private_file(database)
    for suffix in ('-wal', '-shm', '-journal'):
        sidecar = Path(str(database)+suffix)
        if sidecar.exists() or sidecar.is_symlink():
            private_file(sidecar)
    # The Kujo entrypoint remains responsible for the full schema, authority,
    # snapshot binding and transactional operation. Do not duplicate them here.


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('mode')
        validate(sys.argv[1])
    except Exception:
        print(json.dumps({'ok': False, 'code': 'private_admin_config_required'}))
        sys.exit(1)
