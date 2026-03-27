# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
def main():
    print('[1/3] Import...')
    from agent.windows.sync_config import merged_config
    print('[2/3] Aislar entorno...')
    os.environ['PROGRAMDATA'] = tempfile.mkdtemp(prefix='dash_sync_smoke_')
    os.environ['SYNC_LOOP_SECONDS'] = '0'
    os.environ['DBC_DIR'] = tempfile.mkdtemp(prefix='dbc_smoke_')
    os.environ['SUCURSAL_NOMBRE'] = 'SMOKE_TEST'
    os.environ['SUCURSAL_PASSWORD'] = ''
    os.environ['SYNC_API_URL'] = 'http://127.0.0.1:9'
    merged_config()
    import agent_sync
    agent_sync._logger_configured = False
    agent_sync.main()
    print('OK - smoke test terminado.')
    return 0
if __name__ == '__main__': raise SystemExit(main())
