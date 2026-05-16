import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { Calendar, ChevronDown, Filter, RefreshCw, X } from 'lucide-react';
import { useDashboardShell, type DatePreset } from '../../context/DashboardShellContext';

const titles: Record<string, string> = {
  '/': 'Resumen general',
  '/ventas': 'Análisis de ventas',
  '/productos': 'Productos y categorías',
  '/meseros': 'Desempeño meseros',
  '/pagos': 'Métodos de pago',
};

function sameSelection(allIds: string[], selected: string[]): boolean {
  return (
    allIds.length > 0 &&
    selected.length === allIds.length &&
    allIds.every((id) => selected.includes(id))
  );
}

export function DashboardTopbar() {
  const loc = useLocation();
  const title = titles[loc.pathname] ?? 'Dashboard';
  const {
    preset,
    setPreset,
    customDesde,
    customHasta,
    setCustomDesde,
    setCustomHasta,
    selectedSucursalIds,
    setSelectedSucursalIds,
    toggleSucursalId,
    selectAllSucursales,
    sucursales,
    fechaDesde,
    fechaHasta,
    diaOperativo,
    setDiaOperativo,
    operationalCutoffMinutes,
    loading,
    reload,
  } = useDashboardShell();

  const [sucOpen, setSucOpen] = useState(false);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const sucWrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sucOpen) return;
    const onDoc = (e: MouseEvent) => {
      // Si el click fue dentro del wrapper de desktop, no cerrar
      if (sucWrapRef.current && sucWrapRef.current.contains(e.target as Node)) return;
      
      // Si el click fue dentro del portal móvil, no cerrar
      const portal = document.getElementById('mobile-filters-portal');
      if (portal && portal.contains(e.target as Node)) return;

      setSucOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [sucOpen]);

  const periodLabel = useMemo(() => {
    const base = `${fechaDesde} — ${fechaHasta}`;
    if (diaOperativo && operationalCutoffMinutes != null) {
      const h = Math.floor(operationalCutoffMinutes / 60);
      const m = operationalCutoffMinutes % 60;
      const hh = String(h).padStart(2, '0');
      const mm = String(m).padStart(2, '0');
      return `${base} · día operativo (corte ${hh}:${mm})`;
    }
    return base;
  }, [fechaDesde, fechaHasta, diaOperativo, operationalCutoffMinutes]);

  const canDiaOperativo = operationalCutoffMinutes != null;

  const allowedIds = useMemo(() => sucursales.map((s) => s.id), [sucursales]);
  const allSelected = sameSelection(allowedIds, selectedSucursalIds);

  const sucursalButtonLabel = useMemo(() => {
    if (!sucursales.length) return 'Sucursales';
    if (selectedSucursalIds.length === 0) return 'Sin sucursales';
    if (allSelected) return 'Todas las sucursales';
    if (selectedSucursalIds.length === 1) {
      const s = sucursales.find((x) => x.id === selectedSucursalIds[0]);
      return s ? s.nombre.replace(/_/g, ' ') : '1 sucursal';
    }
    return `${selectedSucursalIds.length} sucursales`;
  }, [sucursales, allSelected, selectedSucursalIds]);

  return (
    <header className="shrink-0 border-b border-slate-200 bg-white/90 backdrop-blur px-6 py-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">{title}</h2>
          <p className="text-sm text-slate-500 mt-0.5 font-mono">{periodLabel}</p>
        </div>

        <div className="hidden md:flex flex-wrap items-center gap-3">
          <div className="relative min-w-[200px]" ref={sucWrapRef}>
            <button
              type="button"
              onClick={() => setSucOpen((o) => !o)}
              className="w-full flex items-center justify-between gap-2 text-sm font-semibold rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-sm outline-none focus:ring-2 focus:ring-blue-500"
              aria-expanded={sucOpen}
              aria-haspopup="listbox"
            >
              <span className="truncate text-left">{sucursalButtonLabel}</span>
              <ChevronDown className={`w-4 h-4 shrink-0 text-slate-500 transition ${sucOpen ? 'rotate-180' : ''}`} />
            </button>
            {sucOpen && (
              <div
                className="absolute right-0 z-50 mt-1 w-[min(100vw-2rem,22rem)] rounded-xl border border-slate-200 bg-white py-2 shadow-lg max-h-72 overflow-y-auto"
                role="listbox"
              >
                {!sucursales.length ? (
                  <p className="px-3 py-2 text-sm text-slate-500">Sin sucursales asignadas.</p>
                ) : (
                  <>
                    <label className="flex items-center gap-2 px-3 py-2 text-sm text-slate-800 hover:bg-slate-50 cursor-pointer border-b border-slate-100">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={() => selectAllSucursales()}
                      />
                      <span className="font-semibold">Todas</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => setSelectedSucursalIds([])}
                      className="mx-3 mt-2 mb-1 rounded-lg border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                    >
                      Limpiar selección
                    </button>
                    {sucursales.map((s) => (
                      <label
                        key={s.id}
                        className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selectedSucursalIds.includes(s.id)}
                          onChange={() => toggleSucursalId(s.id)}
                        />
                        <span className="break-words">{s.nombre.replace(/_/g, ' ')}</span>
                      </label>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm">
            <Calendar className="w-4 h-4 text-slate-500 shrink-0" />
            <select
              className="bg-transparent outline-none text-sm font-semibold text-slate-700 cursor-pointer max-w-[160px]"
              value={preset}
              onChange={(e) => setPreset(e.target.value as DatePreset)}
            >
              <option value="hoy">Hoy</option>
              <option value="ayer">Ayer</option>
              <option value="7d">Últimos 7 días</option>
              <option value="30d">Últimos 30 días</option>
              <option value="este_mes">Este mes</option>
              <option value="personalizado">Personalizado</option>
            </select>
          </div>

          <label
            className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm shadow-sm ${
              canDiaOperativo ? 'cursor-pointer border-slate-200 bg-white' : 'cursor-not-allowed border-slate-100 bg-slate-50 text-slate-400'
            }`}
            title={
              canDiaOperativo
                ? 'Filtra por día comercial y presets “Hoy” según corte (todas las sucursales visibles deben compartir el mismo corte).'
                : 'Configura la misma hora de corte en todas las sucursales seleccionadas (Swiss Admin) para habilitar.'
            }
          >
            <input
              type="checkbox"
              checked={diaOperativo}
              disabled={!canDiaOperativo}
              onChange={(e) => setDiaOperativo(e.target.checked)}
            />
            <span className="font-medium text-slate-700">Día operativo</span>
          </label>

          {preset === 'personalizado' && (
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="date"
                value={customDesde}
                onChange={(e) => setCustomDesde(e.target.value)}
                className="text-sm rounded-xl border border-slate-200 px-3 py-2 font-mono"
              />
              <span className="text-slate-400">—</span>
              <input
                type="date"
                value={customHasta}
                onChange={(e) => setCustomHasta(e.target.value)}
                className="text-sm rounded-xl border border-slate-200 px-3 py-2 font-mono"
              />
            </div>
          )}

          <button
            type="button"
            onClick={() => reload()}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800 disabled:opacity-60"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </button>
        </div>
        <div className="md:hidden">
          <button
            type="button"
            onClick={() => setMobileFiltersOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
          >
            <Filter className="h-4 w-4" />
            Filtros
          </button>
        </div>
      </div>
      {mobileFiltersOpen && createPortal(
        <div id="mobile-filters-portal" className="fixed inset-0 z-[9999] md:hidden flex justify-end">
          <div 
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" 
            onClick={() => setMobileFiltersOpen(false)} 
          />
          <div className="relative h-full w-[85%] max-w-sm bg-white shadow-2xl border-l border-slate-200 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0 z-10">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Filtros</h3>
                <p className="text-xs text-slate-500">Personaliza tu vista</p>
              </div>
              <button 
                type="button" 
                onClick={() => setMobileFiltersOpen(false)} 
                className="rounded-full p-2 bg-slate-100 text-slate-500 hover:bg-slate-200 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-5 space-y-6 bg-white">
              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Sucursales</label>
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <button 
                      type="button" 
                      onClick={() => selectAllSucursales()} 
                      className="flex-1 px-3 py-2 text-xs font-bold rounded-lg bg-blue-50 text-blue-700 border border-blue-100"
                    >
                      Todas
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedSucursalIds([])}
                      className="flex-1 px-3 py-2 text-xs font-bold rounded-lg bg-slate-50 text-slate-600 border border-slate-200"
                    >
                      Ninguna
                    </button>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-50">
                    {sucursales.map((s) => (
                      <label 
                        key={s.id} 
                        className="flex items-center gap-3 px-4 py-3 text-sm cursor-pointer active:bg-slate-100 transition-colors"
                      >
                        <input 
                          type="checkbox" 
                          className="w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                          checked={selectedSucursalIds.includes(s.id)} 
                          onChange={() => toggleSucursalId(s.id)} 
                        />
                        <span className="text-slate-700 font-medium">{s.nombre.replace(/_/g, ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Período de tiempo</label>
                <select
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 outline-none focus:ring-2 focus:ring-blue-500 appearance-none transition-all"
                  value={preset}
                  onChange={(e) => setPreset(e.target.value as DatePreset)}
                >
                  <option value="hoy">Hoy</option>
                  <option value="ayer">Ayer</option>
                  <option value="7d">Últimos 7 días</option>
                  <option value="30d">Últimos 30 días</option>
                  <option value="este_mes">Este mes</option>
                  <option value="personalizado">Personalizado</option>
                </select>
              </div>

              {preset === 'personalizado' && (
                <div className="grid grid-cols-1 gap-3 animate-in fade-in slide-in-from-top-2">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-slate-400 ml-1 uppercase">Desde</label>
                    <input 
                      type="date" 
                      value={customDesde} 
                      onChange={(e) => setCustomDesde(e.target.value)} 
                      className="w-full text-sm rounded-xl border border-slate-200 px-4 py-3 font-mono bg-slate-50" 
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-slate-400 ml-1 uppercase">Hasta</label>
                    <input 
                      type="date" 
                      value={customHasta} 
                      onChange={(e) => setCustomHasta(e.target.value)} 
                      className="w-full text-sm rounded-xl border border-slate-200 px-4 py-3 font-mono bg-slate-50" 
                    />
                  </div>
                </div>
              )}

              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Ajustes</label>
                <label
                  className={`flex items-center justify-between gap-2 rounded-xl border p-4 transition-all ${
                    canDiaOperativo 
                      ? 'border-slate-200 bg-white shadow-sm cursor-pointer hover:border-blue-200' 
                      : 'border-slate-100 bg-slate-50 text-slate-400 opacity-60'
                  }`}
                >
                  <span className="text-sm font-semibold text-slate-700">Día operativo</span>
                  <div className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={diaOperativo}
                      disabled={!canDiaOperativo}
                      onChange={(e) => setDiaOperativo(e.target.checked)}
                    />
                    <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </div>
                </label>
                {!canDiaOperativo && (
                  <p className="text-[10px] text-slate-400 leading-tight px-1">
                    Habilita esta opción configurando el mismo corte en Swiss Admin.
                  </p>
                )}
              </div>
            </div>

            <div className="p-5 border-t border-slate-100 bg-slate-50 sticky bottom-0">
              <button
                type="button"
                onClick={() => {
                  reload();
                  setMobileFiltersOpen(false);
                }}
                disabled={loading}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-6 py-4 text-base font-bold text-white shadow-lg active:scale-[0.98] transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Cargando...' : 'Aplicar filtros'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </header>
  );
}
