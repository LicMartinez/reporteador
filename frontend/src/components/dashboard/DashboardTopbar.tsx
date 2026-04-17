import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
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
      if (sucWrapRef.current && !sucWrapRef.current.contains(e.target as Node)) {
        setSucOpen(false);
      }
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
      {mobileFiltersOpen && (
        <div className="fixed inset-0 z-[70] md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileFiltersOpen(false)} />
          <div className="absolute right-0 top-0 h-full w-[88%] max-w-sm bg-white border-l border-slate-200 p-4 overflow-y-auto">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900">Filtros</h3>
              <button type="button" onClick={() => setMobileFiltersOpen(false)} className="rounded-lg p-1 text-slate-500">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="space-y-3">
              <div className="relative" ref={sucWrapRef}>
                <button
                  type="button"
                  onClick={() => setSucOpen((o) => !o)}
                  className="w-full flex items-center justify-between gap-2 text-sm font-semibold rounded-xl border border-slate-200 bg-white px-3 py-2.5"
                >
                  <span className="truncate text-left">{sucursalButtonLabel}</span>
                  <ChevronDown className={`w-4 h-4 shrink-0 text-slate-500 transition ${sucOpen ? 'rotate-180' : ''}`} />
                </button>
              </div>
              {sucOpen && (
                <div className="rounded-xl border border-slate-200 bg-white py-2 max-h-56 overflow-y-auto">
                  <button type="button" onClick={() => selectAllSucursales()} className="w-full px-3 py-2 text-left text-sm font-semibold">
                    Seleccionar todas
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedSucursalIds([])}
                    className="w-full px-3 py-2 text-left text-sm font-semibold text-slate-600"
                  >
                    Limpiar
                  </button>
                  {sucursales.map((s) => (
                    <label key={s.id} className="flex items-center gap-2 px-3 py-2 text-sm">
                      <input type="checkbox" checked={selectedSucursalIds.includes(s.id)} onChange={() => toggleSucursalId(s.id)} />
                      <span>{s.nombre.replace(/_/g, ' ')}</span>
                    </label>
                  ))}
                </div>
              )}
              <select
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
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
              {preset === 'personalizado' && (
                <div className="grid grid-cols-1 gap-2">
                  <input type="date" value={customDesde} onChange={(e) => setCustomDesde(e.target.value)} className="text-sm rounded-xl border border-slate-200 px-3 py-2 font-mono" />
                  <input type="date" value={customHasta} onChange={(e) => setCustomHasta(e.target.value)} className="text-sm rounded-xl border border-slate-200 px-3 py-2 font-mono" />
                </div>
              )}
              <label
                className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                  canDiaOperativo ? 'border-slate-200 bg-white' : 'border-slate-100 bg-slate-50 text-slate-400'
                }`}
              >
                <input
                  type="checkbox"
                  checked={diaOperativo}
                  disabled={!canDiaOperativo}
                  onChange={(e) => setDiaOperativo(e.target.checked)}
                />
                <span className="font-medium">Día operativo</span>
              </label>
              <button
                type="button"
                onClick={() => {
                  reload();
                  setMobileFiltersOpen(false);
                }}
                disabled={loading}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Actualizar
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
