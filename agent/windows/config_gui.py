# -*- coding: utf-8 -*-
"""Dashboard Sync SW - ventana de configuracion (Tkinter)."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path as P

_ROOT = P(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import httpx

import agent_sync

from agent.windows.sync_config import (
    default_config_dict,
    load_config_file,
    save_config_file,
    default_config_path,
)


def main() -> None:
    root = tk.Tk()
    root.title("Dashboard Sync SW — Configuracion")
    root.geometry("760x680")
    root.minsize(680, 620)

    base = default_config_dict()
    file_data = load_config_file()
    cfg = {**base, **file_data}

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frm, text="Dashboard Sync SW", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

    row = 1
    ttk.Label(frm, text="Carpeta DBC (FACTURA1.DBF, etc.):").grid(row=row, column=0, sticky="nw", pady=4)
    dbc_var = tk.StringVar(value=cfg.get("dbc_dir", ""))
    dbc_e = ttk.Entry(frm, textvariable=dbc_var, width=52)
    dbc_e.grid(row=row, column=1, sticky="ew", pady=4)

    def browse():
        d = filedialog.askdirectory(initialdir=dbc_var.get() or "C:/")
        if d:
            dbc_var.set(d)

    ttk.Button(frm, text="Examinar...", command=browse).grid(row=row, column=2, padx=(6, 0), pady=4)
    row += 1 ; frm.columnconfigure(1, weight=1)

    ttk.Label(frm, text="Nombre sucursal (igual que en admin):").grid(row=row, column=0, sticky="w", pady=4)
    nom_var = tk.StringVar(value=cfg.get("sucursal_nombre", ""))
    ttk.Entry(frm, textvariable=nom_var, width=52).grid(row=row, column=1, columnspan=2, sticky="ew", pady=4)
    row += 1

    ttk.Label(frm, text="Contrasena de sincronizacion:").grid(row=row, column=0, sticky="w", pady=4)
    pwd_var = tk.StringVar(value=cfg.get("sucursal_password", ""))
    ttk.Entry(frm, textvariable=pwd_var, width=52, show="*").grid(row=row, column=1, columnspan=2, sticky="ew", pady=4)
    row += 1

    ttk.Label(frm, text="URL del API (sin barra final):").grid(row=row, column=0, sticky="w", pady=4)
    api_var = tk.StringVar(value=cfg.get("sync_api_url", ""))
    ttk.Entry(frm, textvariable=api_var, width=52).grid(row=row, column=1, columnspan=2, sticky="ew", pady=4)
    row += 1

    ttk.Label(frm, text="Clave API sync (opcional, legacy):").grid(row=row, column=0, sticky="w", pady=4)
    key_var = tk.StringVar(value=cfg.get("sync_api_key", ""))
    ttk.Entry(frm, textvariable=key_var, width=52).grid(row=row, column=1, columnspan=2, sticky="ew", pady=4)
    row += 1

    ttk.Label(frm, text="Intervalo bucle (segundos, 0 = una sola corrida):").grid(row=row, column=0, sticky="w", pady=4)
    loop_var = tk.StringVar(value=str(cfg.get("loop_seconds", 300)))
    ttk.Entry(frm, textvariable=loop_var, width=12).grid(row=row, column=1, sticky="w", pady=4)
    row += 1

    ttk.Label(frm, text="Tamano de lote:").grid(row=row, column=0, sticky="w", pady=4)
    batch_var = tk.StringVar(value=str(cfg.get("batch_size", 250)))
    ttk.Entry(frm, textvariable=batch_var, width=12).grid(row=row, column=1, sticky="w", pady=4)
    row += 1

    path_lbl = ttk.Label(frm, text=f"Archivo: {default_config_path()}", font=("Segoe UI", 8), foreground="#555")
    path_lbl.grid(row=row, column=0, columnspan=3, sticky="w", pady=(12, 4))
    row += 1

    prog = ttk.Progressbar(frm, maximum=100.0, mode="determinate")
    prog.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 6))
    row += 1

    status = ttk.Label(frm, text="", font=("Segoe UI", 9))
    status.grid(row=row, column=0, columnspan=3, sticky="w")
    row += 1

    def collect() -> dict:
        try:
            lo = int(loop_var.get().strip() or "0")
        except ValueError:
            lo = 300
        try:
            bs = int(batch_var.get().strip() or "250")
        except ValueError:
            bs = 250
        return {
            "dbc_dir": dbc_var.get().strip(),
            "sucursal_nombre": nom_var.get().strip(),
            "sucursal_password": pwd_var.get(),
            "sync_api_url": api_var.get().strip().rstrip("/"),
            "sync_api_key": key_var.get().strip(),
            "loop_seconds": lo,
            "batch_size": bs,
        }

    def on_save():
        try:
            save_config_file(collect())
            status.config(text="Guardado correctamente.")
            messagebox.showinfo("Dashboard Sync SW", "Configuracion guardada.")
        except OSError as e:
            messagebox.showerror("Error", str(e))

    def on_test():
        url = api_var.get().strip().rstrip("/")
        if not url:
            messagebox.showwarning("API", "Indica la URL del API.")
            return
        try:
            r = httpx.get(url + "/", timeout=15.0)
            if r.status_code != 200:
                messagebox.showwarning("API", f"GET raíz: HTTP {r.status_code}")
                return
        except Exception as e:
            messagebox.showerror("API", f"No se pudo conectar: {e}")
            return

        suc = nom_var.get().strip()
        pwd = pwd_var.get()
        if not suc or not pwd:
            messagebox.showinfo(
                "API",
                "Servidor alcanzable (GET /).\n"
                "Para probar credenciales de sync, rellene nombre de sucursal y contraseña.",
            )
            return

        try:
            up = f"{url}/sync/upload/{suc}"
            headers = {"X-Sucursal-Password": pwd}
            key = key_var.get().strip()
            if key:
                headers["X-API-Key"] = key
            r2 = httpx.post(up, json={"historial": []}, headers=headers, timeout=45.0)
            if r2.status_code == 200:
                messagebox.showinfo("API", f"Sync OK: {r2.text[:500]}")
            else:
                body = (r2.text or "")[:900]
                messagebox.showwarning("API", f"POST sync/upload ? HTTP {r2.status_code}\n{body}")
        except Exception as e:
            messagebox.showerror("API", f"Error en POST sync: {e}")

    _busy = {"v": False}

    def start_worker_detached() -> None:
        if sys.platform != "win32":
            return
        CREATE_NO_WINDOW = 0x08000000
        DETACHED_PROCESS = 0x00000008
        flags = CREATE_NO_WINDOW | DETACHED_PROCESS
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            worker = os.path.join(exe_dir, "DashboardSyncSW.exe")
            if not os.path.isfile(worker):
                return
            args = [worker]
            cwd = exe_dir
        else:
            worker_py = _ROOT / "agent" / "windows" / "worker_main.py"
            if not worker_py.is_file():
                return
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

    def on_exit():
        if _busy["v"]:
            messagebox.showinfo(
                "Dashboard Sync SW",
                "Espere a que termine la carga antes de cerrar la ventana.",
            )
            return
        try:
            save_config_file(collect())
        except OSError:
            pass
        start_worker_detached()
        root.destroy()


    def set_busy(busy: bool):
        _busy["v"] = busy
        st = tk.DISABLED if busy else tk.NORMAL
        for w in action_widgets:
            w.config(state=st)

    def on_progress(msg: str, pct: float) -> None:
        def upd():
            status.config(text=msg)
            prog.config(value=float(pct))

        root.after(0, upd)

    def on_run():
        if _busy["v"]:
            return
        data = collect()
        if not (data.get("dbc_dir") or "").strip():
            messagebox.showwarning("Carga", "Indica la carpeta DBC.")
            return
        if not (data.get("sucursal_nombre") or "").strip():
            messagebox.showwarning("Carga", "Indica el nombre de sucursal.")
            return
        if not (data.get("sync_api_url") or "").strip():
            messagebox.showwarning("Carga", "Indica la URL del API.")
            return
        try:
            save_config_file(data)
        except OSError as e:
            messagebox.showerror("Carga", f"No se pudo guardar la configuracion: {e}")
            return

        set_busy(True)
        prog.config(value=0)
        status.config(text="Iniciando carga…")

        def work():
            try:
                agent_sync._setup_logging()
                result = agent_sync.run_sync_from_gui(on_progress)
            except Exception as e:
                result = {
                    "success": False,
                    "tickets": 0,
                    "nuevas": 0,
                    "errores": 0,
                    "error": str(e),
                }

            def done():
                set_busy(False)
                if not result.get("success"):
                    messagebox.showerror("Carga", result.get("error") or "Error desconocido.")

            root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    hint = ttk.Label(
        frm,
        text="El agente corre en segundo plano sin ventana (Administrador de tareas). "
        "Se inicia al pulsar Salir. "
        "Usa el mayor ORDEN entre checkpoint local y el servidor para continuar. "
        "Si ambos faltan, aplica automaticamente una ventana inicial maxima de 18 meses.",
        font=("Segoe UI", 8),
        foreground="#555",
        wraplength=600,
        justify="left",
    )
    hint.grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))
    row += 1

    bf = ttk.Frame(frm)
    bf.grid(row=row, column=0, columnspan=3, pady=(16, 0))
    btn_save = ttk.Button(bf, text="Guardar", command=on_save)
    btn_save.pack(side=tk.LEFT, padx=(0, 8))
    btn_test = ttk.Button(bf, text="Probar API", command=on_test)
    btn_test.pack(side=tk.LEFT, padx=(0, 8))
    btn_run = ttk.Button(bf, text="Ejecutar carga", command=on_run)
    btn_run.pack(side=tk.LEFT, padx=(0, 8))
    btn_exit = ttk.Button(bf, text="Salir", command=on_exit)
    btn_exit.pack(side=tk.LEFT)
    action_widgets = (btn_save, btn_test, btn_run, btn_exit)

    start_worker_detached()
    root.protocol("WM_DELETE_WINDOW", on_exit)
    root.mainloop()


if __name__ == "__main__":
    main()

