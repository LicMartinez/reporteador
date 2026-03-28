import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Activity, CreditCard, LayoutDashboard, Users } from 'lucide-react';
import { useDashboardShell } from '../../context/DashboardShellContext';
import { KpiCard } from '../../components/dashboard/KpiCard';
import { SectionCard } from '../../components/dashboard/SectionCard';

export default function ResumenPage() {
  const { data, loading } = useDashboardShell();
  const d = data;
  const chartHora = d?.por_hora?.length ? d.por_hora : [{ name: '—', ventas: 0 }];
  const deltas = d?.deltas;

  return (
    <div className="space-y-8">
      {loading && <p className="text-slate-500 text-sm">Cargando…</p>}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard
          title="Ingresos totales"
          value={d?.total_ingresos ?? 0}
          deltaPct={deltas?.total_ingresos_pct ?? null}
          icon={Activity}
        />
        <KpiCard
          title="Tickets"
          value={d?.num_tickets ?? 0}
          deltaPct={deltas?.num_tickets_pct ?? null}
          icon={LayoutDashboard}
          prefix=""
          integer
        />
        <KpiCard
          title="Ticket promedio"
          value={d?.ticket_promedio ?? 0}
          deltaPct={deltas?.ticket_promedio_pct ?? null}
          icon={Users}
        />
        <KpiCard title="Tarjeta (principal)" value={d?.total_tarjeta ?? 0} icon={CreditCard} />
      </div>

      <SectionCard title="Ventas por hora">
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartHora}>
              <defs>
                <linearGradient id="colorVentasResumen" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#64748b', fontSize: 12 }}
                tickFormatter={(value) => `$${value}`}
              />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                formatter={(value) => [`$${value}`, 'Ventas']}
              />
              <Area
                type="monotone"
                dataKey="ventas"
                stroke="#2563eb"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorVentasResumen)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </SectionCard>
    </div>
  );
}
