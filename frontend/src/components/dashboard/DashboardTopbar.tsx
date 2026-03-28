import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { Calendar, RefreshCw } from 'lucide-react';
import { useDashboardShell, type DatePreset } from '../../context/DashboardShellContext';

const titles: Record<string, string> = {
  '/': 'Resumen general',
  '/ventas': 'Análisis de ventas',
  '/productos': 'Productos y categorías',
  '/meseros': 'Desempeño meseros',
  '/pagos': 'Métodos de pago',
};

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
    sucursalId,
    setSucursalId,
    sucursales,
    fechaDesde,
    fechaHasta,
    loading,
    reload,
  } = useDashboardShell();

  const periodLabel = useMemo(
    () => `${fechaDesde} — ${fechaHasta}`,
    [fechaDesde, fechaHasta]
  );

  return (
    <header className="shrink-0 border-b border-slate-200 bg-white/90 backdrop-blur px-6 py-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">{title}</h2>
          <p className="text-sm text-slate-500 mt-0.5 font-mono">{periodLabel}</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            className="text-sm font-semibold rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-sm outline-none focus:ring-2 focus:ring-blue-500 min-w-[200px]"
            value={sucursalId}
            onChange={(e) => setSucursalId(e.target.value)}
          >
            <option value="">Todas (según permisos)</option>
            {sucursales.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nombre.replace(/_/g, ' ')}
              </option>
            ))}
          </select>

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
      </div>
    </header>
  );
}
