import { useDashboardShell } from '../../context/DashboardShellContext';
import { SectionCard } from '../../components/dashboard/SectionCard';

export default function ProductosPage() {
  const { data, loading } = useDashboardShell();
  const rows = data?.top_productos ?? [];

  return (
    <div className="space-y-8">
      {loading && <p className="text-slate-500 text-sm">Cargando…</p>}

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
                <th className="px-4 py-3 font-semibold font-mono">Código</th>
                <th className="px-4 py-3 font-semibold text-right">Cantidad</th>
                <th className="px-4 py-3 font-semibold text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                    Sin datos de productos en este periodo.
                  </td>
                </tr>
              ) : (
                rows.map((r, i) => (
                  <tr key={`${r.nombre}-${i}`} className="border-b border-slate-100 hover:bg-slate-50/80">
                    <td className="px-4 py-3 font-medium text-slate-900">{r.nombre}</td>
                    <td className="px-4 py-3 font-mono text-slate-600">{r.codigo ?? '—'}</td>
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

      <SectionCard title="Categorías">
        <p className="text-slate-600 text-sm">
          Las categorías requieren un catálogo enlazado en el POS o campos adicionales en la sincronización. Próximamente.
        </p>
      </SectionCard>
    </div>
  );
}
