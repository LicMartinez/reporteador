"""Watchdog externo para DashboardSyncSW en Windows.

Monitorea heartbeat del worker y reinicia cuando se detecta stale/hang.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path as P
from typing import Any

_ROOT = P(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent.windows.sync_config import merged_config  # noqa: E402


def _setup_logging(data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    log_path = os.path.join(data_dir, "agent_watchdog.log")
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    if not getattr(sys, "frozen", False):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)


def _read_json(path: str) -> dict[str, Any] | None:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _kill_pid(pid: int) -> None:
    if pid <= 0:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def _service_running(service_name: str) -> bool:
    if not service_name:
        return False
    proc = subprocess.run(
        ["sc", "query", service_name],
        check=False,
        capture_output=True,
        text=True,
    )
    txt = f"{proc.stdout}\n{proc.stderr}".upper()
    return "RUNNING" in txt


def _restart_service(service_name: str) -> bool:
    if not service_name:
        return False
    subprocess.run(["sc", "stop", service_name], check=False, capture_output=True, text=True)
    time.sleep(2)
    start = subprocess.run(["sc", "start", service_name], check=False, capture_output=True, text=True)
    ok = start.returncode == 0
    if not ok:
        logging.error("No se pudo arrancar servicio %s: %s", service_name, start.stderr.strip())
    return ok


def _start_worker_detached() -> bool:
    if sys.platform != "win32":
        return False
    CREATE_NO_WINDOW = 0x08000000
    DETACHED_PROCESS = 0x00000008
    flags = CREATE_NO_WINDOW | DETACHED_PROCESS
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        worker = os.path.join(exe_dir, "DashboardSyncSW.exe")
        if not os.path.isfile(worker):
            return False
        args = [worker]
        cwd = exe_dir
    else:
        worker_py = _ROOT / "agent" / "windows" / "worker_main.py"
        if not worker_py.is_file():
            return False
        args = [sys.executable, str(worker_py)]
        cwd = str(_ROOT)
    subprocess.Popen(
        args,
        cwd=cwd,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    return True


def _parse_iso(s: str | None) -> float | None:
    if not s:
        return None
    try:
        clean = s.replace("Z", "+00:00")
        return float(__import__("datetime").datetime.fromisoformat(clean).timestamp())
    except Exception:
        return None


def main() -> None:
    cfg = merged_config()
    data_dir = cfg.get("data_dir", ".")
    _setup_logging(data_dir)
    if not cfg.get("worker_watchdog_enabled", True):
        logging.info("Watchdog deshabilitado por configuración.")
        return

    hb_path = str(cfg.get("heartbeat_path") or "").strip()
    stale_seconds = max(60, int(cfg.get("worker_stale_threshold_seconds") or 900))
    interval = max(10, int(cfg.get("worker_watchdog_interval_seconds") or 60))
    service_name = str(cfg.get("worker_service_name") or "").strip()

    logging.info(
        "Watchdog iniciado: heartbeat=%s stale=%ss interval=%ss service=%s",
        hb_path,
        stale_seconds,
        interval,
        service_name or "(sin servicio)",
    )

    while True:
        try:
            now = time.time()
            hb = _read_json(hb_path)
            if not hb:
                logging.warning("Sin heartbeat legible; intentando arrancar worker.")
                if service_name and _service_running(service_name):
                    logging.info("Servicio %s ya está corriendo.", service_name)
                elif service_name:
                    _restart_service(service_name)
                else:
                    _start_worker_detached()
                time.sleep(interval)
                continue

            pid = int(hb.get("pid") or 0)
            last_hb_ts = _parse_iso(str(hb.get("last_heartbeat_at") or ""))
            phase = str(hb.get("phase") or "")
            alive = _pid_alive(pid)
            stale = last_hb_ts is None or (now - last_hb_ts) > stale_seconds

            if alive and not stale:
                logging.info("Worker saludable pid=%s fase=%s", pid, phase)
                time.sleep(interval)
                continue

            logging.warning(
                "Worker stale/no vivo (pid=%s alive=%s stale=%s phase=%s). Reiniciando.",
                pid,
                alive,
                stale,
                phase,
            )
            if alive:
                _kill_pid(pid)
                time.sleep(2)

            restarted = False
            if service_name:
                restarted = _restart_service(service_name)
            if not restarted:
                _start_worker_detached()
        except Exception as exc:
            logging.exception("Error watchdog: %s", exc)
        time.sleep(interval)


if __name__ == "__main__":
    main()
