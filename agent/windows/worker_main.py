"""Punto de entrada PyInstaller: servicio Dashboard Sync SW."""
from __future__ import annotations

import sys
from pathlib import Path as P

_ROOT = P(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import agent_sync

if __name__ == "__main__":
    agent_sync.main()
