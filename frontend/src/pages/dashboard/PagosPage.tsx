import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useDashboardShell } from '../../context/DashboardShellContext';
import { SectionCard } from '../../components/dashboard/SectionCard';

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#6366f1', '#ec4899', '#14b8a6', '#f97316'];

export default function PagosPage() {
  const { data, loading } = useDashboardShell();
  const chartMetodo = data?.por_metodo?.length ? data.por_metodo : [{ name: '—', amount: 0 }];

  return (
    <div className="space-y-8">
      {loading && <p className="text-slate-500 text-sm">Cargando…</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SectionCard title="Distribución por método">
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartMetodo}
                  dataKey="amount"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={56}
                  outerRadius={100}
                  paddingAngle={2}
                >
                  {chartMetodo.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="transparent" />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => [`$${Number(value ?? 0).toLocaleString('es-MX')}`, 'Monto']}
                  contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-4 flex flex-wrap gap-2 justify-center">
            {chartMetodo.map((m, i) => (
              <li key={m.name} className="text-xs flex items-center gap-1.5 text-slate-600">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                {m.name}: ${Number(m.amount).toLocaleString('es-MX')}
              </li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard title="Montos por método (barras)">
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartMetodo} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" hide />
                <YAxis
                  dataKey="name"
                  type="category"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#475569', fontSize: 11 }}
                  width={110}
                />
                <Tooltip
                  cursor={{ fill: '#f1f5f9' }}
                  contentStyle={{ borderRadius: 12, border: 'none' }}
                  formatter={(value) => [`$${Number(value ?? 0).toLocaleString('es-MX')}`, 'Monto']}
                />
                <Bar dataKey="amount" radius={[0, 6, 6, 0]} barSize={26}>
                  {chartMetodo.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
