import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useDashboardShell } from '../../context/DashboardShellContext';
import { SectionCard } from '../../components/dashboard/SectionCard';

function claseLabel(claseKey: number): string {
  switch (claseKey) {
    case 1:
      return 'BEBIDAS';
    case 2:
      return 'ALIMENTOS';
    default:
      return 'OTROS ARTÍCULOS';
  }
}

export default function ProductosPage() {
  const { data, loading } = useDashboardShell();
  const [searchParams, setSearchParams] = useSearchParams();
  const rows = data?.top_productos ?? [];
  const porClase = data?.por_clase ?? [];

  const claseParam = searchParams.get('clase');
  const filtroClase =
    claseParam === '1' || claseParam === '2' || claseParam === '3' ? Number(claseParam) : null;

  const setClaseFiltro = useCallback(
    (k: number | null) => {
      const next = new URLSearchParams(searchParams);
      if (k == null) {
        next.delete('clase');
      } else {
        next.set('clase', String(k));
      }
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  const displayedRows = useMemo(() => {
    if (filtroClase == null) return rows;
    return rows.filter((r) => (r.clase ?? 3) === filtroClase);
  }, [rows, filtroClase]);

  return (
    <div className="space-y-8">
      {loading && <p className="text-slate-500 text-sm">Cargando…</p>}

      {filtroClase != null && (
        <p className="text-sm text-slate-600">
          Filtrando por <span className="font-semibold">{claseLabel(filtroClase)}</span>.{' '}
          <button
            type="button"
            className="text-blue-600 font-semibold hover:text-blue-700"
            onClick={() => setClaseFiltro(null)}
          >
            Quitar filtro
          </button>
        </p>
      )}

      <SectionCard title="Top productos (por total de renglón)">
        <p className="text-sm text-slate-500 mb-4">
          Agregado desde <span className="font-mono">detalles</span> de cada ticket. Costo y margen no están disponibles en la
          sincronización actual.
        </p>
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 text-left text-slate-600 border-b border-slate-200">
                <th className="px-4 py-3 font-semibold">Producto</th>
                <th className="px-4 py-3 font-semibold text-right">Cantidad</th>
                <th className="px-4 py-3 font-semibold text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {displayedRows.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-slate-500">
                    {filtroClase != null
                      ? 'Sin productos en esta categoría en el periodo.'
                      : 'Sin datos de productos en este periodo.'}
                  </td>
                </tr>
              ) : (
                displayedRows.map((r, i) => (
                  <tr key={`${r.nombre}-${i}`} className="border-b border-slate-100 hover:bg-slate-50/80">
                    <td className="px-4 py-3 font-medium text-slate-900">{r.nombre}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{r.cantidad.toLocaleString('es-MX')}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-medium">
                      ${r.total_renglon.toLocaleString('es-MX')}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <SectionCard title="Por tipo de ítem">
        <p className="text-sm text-slate-500 mb-4">
          Agrupación por clase de renglón en el POS: bebidas, alimentos y otros artículos. Pulsa una fila para filtrar el top de
          productos arriba.
        </p>
        {porClase.length === 0 ? (
          <p className="text-slate-600 text-sm">Sin renglones clasificados en este periodo.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 text-left text-slate-600 border-b border-slate-200">
                  <th className="px-4 py-3 font-semibold">Tipo</th>
                  <th className="px-4 py-3 font-semibold text-right">Cantidad</th>
                  <th className="px-4 py-3 font-semibold text-right">Total renglón</th>
                </tr>
              </thead>
              <tbody>
                {porClase.map((c) => {
                  const active = filtroClase === c.clase_key;
                  return (
                    <tr
                      key={c.clase_key}
                      onClick={() => setClaseFiltro(active ? null : c.clase_key)}
                      className={`border-b border-slate-100 cursor-pointer transition-colors ${
                        active ? 'bg-blue-50/90' : 'hover:bg-slate-50/80'
                      }`}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setClaseFiltro(active ? null : c.clase_key);
                        }
                      }}
                    >
                      <td className="px-4 py-3 font-medium text-slate-900">{c.name}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{c.cantidad.toLocaleString('es-MX')}</td>
                      <td className="px-4 py-3 text-right tabular-nums font-medium">
                        ${c.total_renglon.toLocaleString('es-MX')}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
