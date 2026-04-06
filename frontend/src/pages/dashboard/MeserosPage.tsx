import { UserCircle } from 'lucide-react';
import { useDashboardShell } from '../../context/DashboardShellContext';
import { SectionCard } from '../../components/dashboard/SectionCard';

export default function MeserosPage() {
  const { data, loading } = useDashboardShell();
  const rows = data?.por_mesero ?? [];

  return (
    <SectionCard title="Desempeño por mesero">
      {loading && <p className="text-slate-500 text-sm mb-4">Cargando…</p>}
      {rows.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
            <UserCircle className="w-8 h-8 text-slate-400" />
          </div>
          <p className="text-slate-800 font-semibold mb-2">Sin datos de mesero en este periodo</p>
          <p className="text-slate-600 text-sm max-w-md">
            El agente envía <span className="font-mono">MESERO</span> desde FACTURA1 y el nombre desde MESEROS.DBF cuando está
            disponible. Si el POS no asigna mesero a los tickets, aquí no habrá filas.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 text-left text-slate-600 border-b border-slate-200">
                <th className="px-4 py-3 font-semibold">Mesero</th>
                <th className="px-4 py-3 font-semibold font-mono">Código</th>
                <th className="px-4 py-3 font-semibold text-right">Tickets</th>
                <th className="px-4 py-3 font-semibold text-right">Total vendido</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.codigo} className="border-b border-slate-100 hover:bg-slate-50/80">
                  <td className="px-4 py-3 font-medium text-slate-900">{r.nombre}</td>
                  <td className="px-4 py-3 font-mono text-slate-600">{r.codigo}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{r.num_tickets.toLocaleString('es-MX')}</td>
                  <td className="px-4 py-3 text-right tabular-nums font-medium">
                    ${r.total_pagado.toLocaleString('es-MX')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </SectionCard>
  );
}
