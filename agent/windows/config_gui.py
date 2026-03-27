# -*- coding: utf-8 -*-
"""Dashboard Sync SW — ventana de configuracion (Tkinter)."""
from __future__ import annotations

import sys
from pathlib import Path as P

_ROOT = P(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import httpx

from agent.windows.sync_config import (
    default_config_dict,
    load_config_file,
    save_config_file,
    default_config_path,
)


def main() -> None:
    root = tk.Tk()
    root.title("Dashboard Sync SW — Configuracion")
    root.geometry("640x520")
    root.minsize(560, 440)

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
            if r.status_code == 200:
                messagebox.showinfo("API", "Respuesta OK del servidor.")
            else:
                messagebox.showwarning("API", f"HTTP {r.status_code}")
        except Exception as e:
            messagebox.showerror("API", f"No se pudo conectar: {e}")

    bf = ttk.Frame(frm)
    bf.grid(row=row, column=0, columnspan=3, pady=(16, 0))
    ttk.Button(bf, text="Guardar", command=on_save).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(bf, text="Probar API", command=on_test).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(bf, text="Salir", command=root.destroy).pack(side=tk.LEFT)

    root.mainloop()


if __name__ == "__main__":
    main()
