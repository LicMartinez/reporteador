import { useMemo } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Banknote, CalendarDays, CreditCard, LayoutDashboard, TrendingUp, Wallet } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';
import { Link } from 'react-router-dom';
import { useDashboardShell } from '../../context/DashboardShellContext';
import { KpiCard } from '../../components/dashboard/KpiCard';
import { SectionCard } from '../../components/dashboard/SectionCard';
const PIE_COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#64748b'];

function fmtShortMoney(n: number) {
  if (n >= 1000) return `$${(n / 1000).toFixed(1)}k`;
  return `$${Math.round(n)}`;
}

function labelDiaCorto(fecha: string) {
  const s = (fecha || '').slice(0, 10);
  try {
    return format(parseISO(s), 'EEE d', { locale: es });
  } catch {
    return s;
  }
}

function bucketVentasPorHora(rows: { name: string; ventas: number }[]) {
  const buckets: Record<string, number> = {};
  for (const r of rows) {
    const raw = (r.name || '00:00').trim();
    const hour = raw.slice(0, 2).replace(/\D/g, '') || '0';
    const h = hour.length === 1 ? `0${hour}` : hour.slice(0, 2);
    buckets[h] = (buckets[h] || 0) + r.ventas;
  }
  const keys = Object.keys(buckets).sort();
  if (!keys.length) return [{ name: '—', ventas: 0 }];
  return keys.map((h) => ({ name: `${h}:00`, ventas: Math.round(buckets[h] * 100) / 100 }));
}

function TooltipOscuro({ active, payload, label }: { active?: boolean; payload?: { name?: string; value?: number; color?: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg bg-slate-800 px-3 py-2 text-xs shadow-lg border border-slate-700">
      <p className="text-slate-400 font-semibold mb-1">{label}</p>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2 text-slate-100">
          <span className="h-2 w-2 rounded-full shrink-0" style={{ background: p.color }} />
          <span className="text-slate-400">{p.name}:</span>
          <span className="font-bold">{typeof p.value === 'number' ? fmtShortMoney(p.value) : p.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function ResumenPage() {
  const { data, loading } = useDashboardShell();
  const d = data;

  const chartDia = useMemo(() => {
    const rows = d?.por_dia ?? [];
    if (!rows.length) return [{ dia: '—', ingreso: 0 }];
    return rows.map((r) => ({
      dia: labelDiaCorto(r.fecha),
      ingreso: r.total_pagado,
    }));
  }, [d?.por_dia]);

  const chartHora = useMemo(() => bucketVentasPorHora(d?.por_hora?.length ? d.por_hora : []), [d?.por_hora]);

  const pieMetodos = useMemo(() => {
    const m = d?.por_metodo ?? [];
    const total = m.reduce((a, x) => a + x.amount, 0) || 1;
    return m.map((x) => ({ ...x, pct: Math.round((x.amount / total) * 100) }));
  }, [d?.por_metodo]);

  const maxClase = useMemo(() => {
    const c = d?.por_clase ?? [];
    return Math.max(...c.map((x) => x.total_renglon), 1);
  }, [d?.por_clase]);

  const topMeseros = (d?.por_mesero ?? []).slice(0, 5);
  const diasConVentas = d?.por_dia?.length ?? 0;

  return (
    <div className="space-y-6">
      {loading && <p className="text-slate-500 text-sm">Cargando…</p>}

      <p className="text-xs text-slate-500 -mt-2 max-w-3xl leading-relaxed">
        Este resumen usa datos reales del POS (sincronización). Los costos, márgenes y utilidad del mockup de diseño no están
        en la API aún: requerirían costo por renglón (p. ej. COSVEN en DBF) agregado en backend.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6 gap-3">
        <KpiCard
          title="Ingresos totales"
          value={d?.total_ingresos ?? 0}
          deltaPct={d?.deltas?.total_ingresos_pct ?? null}
          icon={TrendingUp}
          accent="blue"
          subtitle="Incluye IVA (ventas registradas)"
        />
        <KpiCard
          title="Efectivo"
          value={d?.total_efectivo ?? 0}
          icon={Banknote}
          accent="green"
        />
        <KpiCard
          title="Tickets"
          value={d?.num_tickets ?? 0}
          deltaPct={d?.deltas?.num_tickets_pct ?? null}
          icon={LayoutDashboard}
          prefix=""
          integer
          accent="purple"
          subtitle="Cuentas en el periodo"
        />
        <KpiCard
          title="Ticket promedio"
          value={d?.ticket_promedio ?? 0}
          deltaPct={d?.deltas?.ticket_promedio_pct ?? null}
          icon={Wallet}
          accent="teal"
          subtitle="Por cuenta"
        />
        <KpiCard
          title="Tarjeta (principal)"
          value={d?.total_tarjeta ?? 0}
          icon={CreditCard}
          accent="rose"
          subtitle="Suma medios tipo tarjeta"
        />
        <KpiCard
          title="Días con ventas"
          value={diasConVentas}
          icon={CalendarDays}
          prefix=""
          integer
          accent="amber"
          subtitle="Días distintos con tickets"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <SectionCard title="Ventas diarias (ingreso)" className="xl:col-span-2">
          <p className="text-xs text-slate-500 mb-3">Total pagado por día calendario en el rango seleccionado.</p>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartDia} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gIngresoDia" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="dia" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis
                  tickFormatter={fmtShortMoney}
                  tick={{ fontSize: 11, fill: '#94a3b8' }}
                  axisLine={false}
                  tickLine={false}
                  width={44}
                />
                <Tooltip content={<TooltipOscuro />} />
                <Area
                  type="monotone"
                  dataKey="ingreso"
                  name="Ingreso"
                  stroke="#2563eb"
                  strokeWidth={2}
                  fill="url(#gIngresoDia)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>

        <SectionCard title="Métodos de pago">
          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieMetodos}
                  cx="50%"
                  cy="50%"
                  innerRadius={44}
                  outerRadius={68}
                  dataKey="amount"
                  paddingAngle={2}
                  nameKey="name"
                >
                  {pieMetodos.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v) =>
                    typeof v === 'number'
                      ? v.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })
                      : String(v ?? '')
                  }
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-2 space-y-1.5 text-sm">
            {pieMetodos.map((m, i) => (
              <li key={m.name} className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 min-w-0 text-slate-600">
                  <span className="h-2 w-2 rounded-full shrink-0" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                  <span className="truncate">{m.name}</span>
                </span>
                <span className="font-mono font-semibold text-slate-900 shrink-0">{m.pct}%</span>
              </li>
            ))}
            {!pieMetodos.length && <li className="text-slate-500">Sin datos de medios de pago.</li>}
          </ul>
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SectionCard
          title="Por clase (producto)"
          action={
            <Link to="/productos" className="text-xs font-semibold text-blue-600 hover:text-blue-700">
              Ver productos
            </Link>
          }
        >
          <p className="text-xs text-slate-500 mb-3">Suma de renglones por CLASE en tickets (cuando el POS la envía).</p>
          <div className="space-y-3">
            {(d?.por_clase ?? []).slice(0, 6).map((c) => (
              <div key={c.name}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium text-slate-700">{c.name}</span>
                  <span className="font-mono font-semibold text-slate-900">
                    {c.total_renglon.toLocaleString('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 })}
                  </span>
                </div>
                <div className="h-1.5 rounded bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded bg-blue-500 transition-all"
                    style={{ width: `${Math.min(100, Math.round((c.total_renglon / maxClase) * 100))}%` }}
                  />
                </div>
              </div>
            ))}
            {!(d?.por_clase ?? []).length && <p className="text-sm text-slate-500">Sin desglose por clase en este periodo.</p>}
          </div>
        </SectionCard>

        <SectionCard
          title="Ranking de meseros"
          action={
            <Link to="/meseros" className="text-xs font-semibold text-blue-600 hover:text-blue-700">
              Ver desempeño
            </Link>
          }
        >
          <div className="space-y-2">
            {topMeseros.map((m, i) => {
              const maxV = topMeseros[0]?.total_pagado || 1;
              const w = Math.round((m.total_pagado / maxV) * 100);
              return (
                <div key={m.codigo} className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0">
                  <span className="text-lg w-7 text-center shrink-0">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}.`}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between gap-2 text-sm">
                      <span className="font-semibold text-slate-800 truncate">{m.nombre}</span>
                      <span className="font-mono font-bold text-slate-900 shrink-0">
                        {m.total_pagado.toLocaleString('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 })}
                      </span>
                    </div>
                    <div className="mt-1 h-1 rounded bg-slate-100 overflow-hidden">
                      <div className="h-full rounded bg-violet-500" style={{ width: `${w}%` }} />
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      {m.num_tickets} tickets · prom{' '}
                      {(m.num_tickets ? m.total_pagado / m.num_tickets : 0).toLocaleString('es-MX', {
                        style: 'currency',
                        currency: 'MXN',
                        maximumFractionDigits: 0,
                      })}
                    </p>
                  </div>
                </div>
              );
            })}
            {!topMeseros.length && (
              <p className="text-sm text-slate-500">Sin datos de mesero en el periodo (revisa sync y MESERO en DBF).</p>
            )}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Ventas por hora del día (agrupadas)">
        <p className="text-xs text-slate-500 mb-3">
          Suma por hora del reloj. Antes veías un punto por cada hora exacta del ticket (p. ej. 23:57); aquí se agrupa por hora para
          acercarse al mockup y mejorar la lectura.
        </p>
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
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#64748b', fontSize: 11 }}
                tickFormatter={fmtShortMoney}
                width={48}
              />
              <Tooltip content={<TooltipOscuro />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area
                type="monotone"
                dataKey="ventas"
                name="Ventas"
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
