"""Punto de entrada PyInstaller: servicio Dashboard Sync SW."""
from __future__ import annotations

import sys
from pathlib import Path as P

_ROOT = P(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _exit_if_second_worker_instance() -> None:
    """Un solo proceso worker; evita varios bucles al cerrar la GUI varias veces."""
    if sys.platform != "win32":
        return
    import ctypes

    ERROR_ALREADY_EXISTS = 183
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\DashboardSyncSW_WorkerMutex_v1")
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        sys.exit(0)


if __name__ == "__main__":
    _exit_if_second_worker_instance()
    import agent_sync

    agent_sync.main()
