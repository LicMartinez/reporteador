import { useState } from 'react';
import { createPortal } from 'react-dom';
import { Calendar, Check, ChevronDown, RefreshCw, X } from 'lucide-react';
import { useDashboardShell, type DatePreset } from '../../context/DashboardShellContext';

const presetLabels: Record<DatePreset, string> = {
  hoy: 'Hoy',
  ayer: 'Ayer',
  '7d': '7 días',
  '30d': '30 días',
  este_mes: 'Mes',
  personalizado: 'Custom',
};

export function MobileFilterBar() {
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
    loading,
    reload,
  } = useDashboardShell();

  const [sucursalSheetOpen, setSucursalSheetOpen] = useState(false);
  const [dateSheetOpen, setDateSheetOpen] = useState(false);

  const allSelected =
    sucursales.length > 0 &&
    selectedSucursalIds.length === sucursales.length &&
    sucursales.every((s) => selectedSucursalIds.includes(s.id));

  const sucLabel = allSelected
    ? 'Todas'
    : selectedSucursalIds.length === 0
      ? 'Ninguna'
      : selectedSucursalIds.length === 1
        ? (sucursales.find((s) => s.id === selectedSucursalIds[0])?.nombre.replace(/_/g, ' ') ?? '1')
        : `${selectedSucursalIds.length} suc.`;

  return (
    <>
      {/* Sticky filter bar */}
      <div className="md:hidden sticky top-0 z-30 bg-white border-b border-slate-100 px-3 py-2 safe-area-top">
        <div className="flex items-center gap-2">
          {/* Sucursal chip */}
          <button
            type="button"
            onClick={() => setSucursalSheetOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-full bg-slate-100 text-xs font-semibold text-slate-700 active:bg-slate-200 min-h-[36px]"
          >
            <span className="truncate max-w-[80px]">{sucLabel}</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {/* Date preset pills */}
          <div className="flex-1 flex items-center gap-1 overflow-x-auto no-scrollbar">
            {(['hoy', 'ayer', '7d', '30d', 'este_mes'] as DatePreset[]).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPreset(p)}
                className={`shrink-0 px-3 py-2 rounded-full text-xs font-semibold min-h-[36px] transition-colors ${
                  preset === p
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-600 active:bg-slate-200'
                }`}
              >
                {presetLabels[p]}
              </button>
            ))}
            <button
              type="button"
              onClick={() => {
                setPreset('personalizado');
                setDateSheetOpen(true);
              }}
              className={`shrink-0 px-3 py-2 rounded-full text-xs font-semibold min-h-[36px] transition-colors ${
                preset === 'personalizado'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-600 active:bg-slate-200'
              }`}
            >
              <Calendar className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Refresh */}
          <button
            type="button"
            onClick={() => reload()}
            disabled={loading}
            className="shrink-0 p-2 rounded-full bg-slate-900 text-white min-h-[36px] min-w-[36px] flex items-center justify-center active:bg-slate-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Sucursal bottom sheet */}
      {sucursalSheetOpen &&
        createPortal(
          <div className="fixed inset-0 z-[9999] md:hidden">
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setSucursalSheetOpen(false)}
            />
            <div className="absolute bottom-0 left-0 right-0 bg-white rounded-t-2xl max-h-[70vh] flex flex-col animate-in slide-in-from-bottom duration-200 safe-area-bottom">
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
                <h3 className="text-base font-bold text-slate-900">Sucursales</h3>
                <button
                  type="button"
                  onClick={() => setSucursalSheetOpen(false)}
                  className="p-2 rounded-full bg-slate-100 active:bg-slate-200"
                >
                  <X className="w-4 h-4 text-slate-600" />
                </button>
              </div>

              <div className="flex gap-2 px-5 py-3 border-b border-slate-50">
                <button
                  type="button"
                  onClick={() => selectAllSucursales()}
                  className="flex-1 py-2.5 rounded-xl text-sm font-bold bg-blue-50 text-blue-700 active:bg-blue-100"
                >
                  Todas
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedSucursalIds([])}
                  className="flex-1 py-2.5 rounded-xl text-sm font-bold bg-slate-100 text-slate-600 active:bg-slate-200"
                >
                  Ninguna
                </button>
              </div>

              <div className="flex-1 overflow-y-auto">
                {sucursales.map((s) => {
                  const checked = selectedSucursalIds.includes(s.id);
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => toggleSucursalId(s.id)}
                      className="w-full flex items-center gap-3 px-5 py-3.5 active:bg-slate-50 text-left"
                    >
                      <div
                        className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-colors ${
                          checked
                            ? 'bg-blue-600 border-blue-600'
                            : 'border-slate-300 bg-white'
                        }`}
                      >
                        {checked && <Check className="w-4 h-4 text-white" />}
                      </div>
                      <span className="text-sm font-medium text-slate-800">
                        {s.nombre.replace(/_/g, ' ')}
                      </span>
                    </button>
                  );
                })}
              </div>

              <div className="px-5 py-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    reload();
                    setSucursalSheetOpen(false);
                  }}
                  className="w-full py-3.5 rounded-xl bg-slate-900 text-white text-sm font-bold active:bg-slate-700"
                >
                  Aplicar
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* Custom date bottom sheet */}
      {dateSheetOpen &&
        createPortal(
          <div className="fixed inset-0 z-[9999] md:hidden">
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setDateSheetOpen(false)}
            />
            <div className="absolute bottom-0 left-0 right-0 bg-white rounded-t-2xl flex flex-col animate-in slide-in-from-bottom duration-200 safe-area-bottom">
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
                <h3 className="text-base font-bold text-slate-900">Rango personalizado</h3>
                <button
                  type="button"
                  onClick={() => setDateSheetOpen(false)}
                  className="p-2 rounded-full bg-slate-100 active:bg-slate-200"
                >
                  <X className="w-4 h-4 text-slate-600" />
                </button>
              </div>

              <div className="px-5 py-5 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Desde</label>
                  <input
                    type="date"
                    value={customDesde}
                    onChange={(e) => setCustomDesde(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-base font-mono bg-slate-50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1.5">Hasta</label>
                  <input
                    type="date"
                    value={customHasta}
                    onChange={(e) => setCustomHasta(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-base font-mono bg-slate-50"
                  />
                </div>
              </div>

              <div className="px-5 py-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    reload();
                    setDateSheetOpen(false);
                  }}
                  className="w-full py-3.5 rounded-xl bg-slate-900 text-white text-sm font-bold active:bg-slate-700"
                >
                  Aplicar
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </>
  );
}
