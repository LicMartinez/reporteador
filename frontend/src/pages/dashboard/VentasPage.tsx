import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useDashboardShell } from '../../context/DashboardShellContext';
import { SectionCard } from '../../components/dashboard/SectionCard';

export default function VentasPage() {
  const { data, loading } = useDashboardShell();
  const porDia = data?.por_dia?.length
    ? data.por_dia.map((row) => ({
        fecha: row.fecha.length >= 10 ? row.fecha.slice(5) : row.fecha || '—',
        total: row.total_pagado,
        tickets: row.num_tickets,
      }))
    : [{ fecha: '—', total: 0, tickets: 0 }];

  return (
    <div className="space-y-8">
      {loading && <p className="text-slate-500 text-sm">Cargando…</p>}

      <SectionCard title="Ingresos por día">
        <p className="text-sm text-slate-500 mb-4">
          Barras según ventas consolidadas en el rango seleccionado (suma de <span className="font-mono">total_pagado</span> por
          fecha).
        </p>
        <div className="h-96 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={porDia} margin={{ bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="fecha" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#64748b', fontSize: 11 }}
                tickFormatter={(v) => `$${v}`}
              />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: 'none' }}
                formatter={(value, name) =>
                  name === 'total'
                    ? [`$${Number(value ?? 0).toLocaleString('es-MX')}`, 'Ingresos']
                    : [String(value ?? ''), 'Tickets']
                }
                labelFormatter={(label) => `Día ${label}`}
              />
              <Bar dataKey="total" fill="#3b82f6" name="total" radius={[6, 6, 0, 0]} maxBarSize={48} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </SectionCard>

      <SectionCard title="Ventas por hora (mismo periodo)">
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data?.por_hora?.length ? data.por_hora : [{ name: '—', ventas: 0 }]}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#64748b', fontSize: 11 }}
                tickFormatter={(v) => `$${v}`}
              />
              <Tooltip
                formatter={(v) => [`$${Number(v ?? 0)}`, 'Ventas']}
                contentStyle={{ borderRadius: 12, border: 'none' }}
              />
              <Bar dataKey="ventas" fill="#6366f1" radius={[6, 6, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </SectionCard>
    </div>
  );
}
