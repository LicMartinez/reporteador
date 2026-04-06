import { useMemo } from 'react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertTriangle, Banknote, Box, RefreshCw, TrendingUp } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';
import { useDashboardShell } from '../../context/DashboardShellContext';
import { SectionCard } from '../../components/dashboard/SectionCard';
import { KpiCard } from '../../components/dashboard/KpiCard';

const WD_ORDER = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'] as const;
const WD_COLORS: Record<(typeof WD_ORDER)[number], string> = {
  Lun: '#2563eb',
  Mar: '#7c3aed',
  Mié: '#10b981',
  Jue: '#64748b',
  Vie: '#0ea5e9',
  Sáb: '#8b5cf6',
  Dom: '#94a3b8',
};

function fmtShortMoney(n: number) {
  if (Math.abs(n) >= 1000) return `$${(n / 1000).toFixed(1)}k`;
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

function TooltipOscuro({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name?: string; value?: number; color?: string }[];
  label?: string;
}) {
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

export default function VentasPage() {
  const { data, loading } = useDashboardShell();
  const d = data;
  const deltas = d?.deltas;

  const tieneCosto = (d?.total_costo ?? 0) > 0;

  const chartDia = useMemo(() => {
    const rows = d?.por_dia ?? [];
    if (!rows.length) return [{ dia: '—', ingreso: 0, costo: 0, tickets: 0 }];
    return rows.map((r) => ({
      dia: labelDiaCorto(r.fecha),
      ingreso: r.total_pagado,
      costo: r.total_costo ?? 0,
      tickets: r.num_tickets,
    }));
  }, [d?.por_dia]);

  const chartHoraSemana = useMemo(() => {
    const rows = d?.por_hora_semana ?? [];
    if (!rows.length) return [];
    return rows.map((r) => {
      const row: Record<string, string | number> = { hora: r.hora };
      for (const w of WD_ORDER) {
        row[w] = r[w] ?? 0;
      }
      return row;
    });
  }, [d?.por_hora_semana]);

  const rf = d?.resumen_financiero;

  const pctCostoIngreso =
    d && d.total_ingresos > 0 ? Math.round(((d.total_costo ?? 0) / d.total_ingresos) * 1000) / 10 : 0;

  return (
    <div className="space-y-8">
      {loading && <p className="text-slate-500 text-sm">Cargando…</p>}

      <p className="text-xs text-slate-500 -mt-2 max-w-3xl leading-relaxed">
        Costo y margen usan <span className="font-mono">COSVEN</span> en FACTURA2 cuando el agente lo sincroniza. Las
        anulaciones no se importan hoy (tickets cancelados se excluyen del histórico). IVA al 16&nbsp;% sobre total
        cobrado (estimado). Comisiones de tarjeta son aproximación por nombre de método.
      </p>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          title="Ventas del período"
          value={d?.total_ingresos ?? 0}
          deltaPct={deltas?.total_ingresos_pct ?? null}
          icon={Banknote}
          accent="blue"
          subtitle="incl. IVA"
        />
        <KpiCard
          title="Utilidad bruta"
          value={d?.utilidad_bruta ?? 0}
          deltaPct={deltas?.utilidad_bruta_pct ?? null}
          icon={TrendingUp}
          accent="green"
          subtitle={
            tieneCosto && d?.margen_pct != null
              ? `${d.margen_pct}% margen sobre ingreso`
              : tieneCosto
                ? 'sin % de margen'
                : 'Sin costo en detalles (re-sincronizar con agente actualizado)'
          }
        />
        <KpiCard
          title="Costo total"
          value={d?.total_costo ?? 0}
          deltaPct={deltas?.total_costo_pct ?? null}
          icon={Box}
          accent="amber"
          subtitle={d?.total_ingresos ? `${pctCostoIngreso}% del ingreso` : undefined}
        />
        <KpiCard
          title="Anulaciones"
          value={d?.total_anulaciones_monto ?? 0}
          icon={AlertTriangle}
          accent="rose"
          subtitle={
            (d?.total_anulaciones_monto ?? 0) === 0
              ? 'No hay monto de anulaciones en datos importados'
              : '% del ingreso bruto (cuando exista fuente)'
          }
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <SectionCard title="Ingreso · Costo · Tickets por día" className="xl:col-span-2">
          <div className="h-[380px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartDia} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="dia" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis
                  yAxisId="left"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  tickFormatter={(v) => fmtShortMoney(Number(v))}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                />
                <Tooltip content={<TooltipOscuro />} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar yAxisId="left" dataKey="ingreso" name="Ingreso" fill="#2563eb" radius={[4, 4, 0, 0]} maxBarSize={28} />
                <Bar yAxisId="left" dataKey="costo" name="Costo" fill="#fbbf24" radius={[4, 4, 0, 0]} maxBarSize={28} />
                <Bar
                  yAxisId="right"
                  dataKey="tickets"
                  name="Tickets"
                  fill="#8b5cf6"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={28}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>

        <SectionCard
          title="Resumen financiero"
          action={
            <span className="inline-flex items-center gap-1 text-xs text-slate-400">
              <RefreshCw className="w-3.5 h-3.5" />
              API
            </span>
          }
        >
          {!rf ? (
            <p className="text-sm text-slate-500">Sin datos financieros agregados.</p>
          ) : (
            <ul className="space-y-3 text-sm">
              <li className="flex justify-between gap-2">
                <span className="text-slate-600">Ingreso bruto</span>
                <span className="font-mono font-semibold text-blue-600">
                  ${rf.ingreso_bruto.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
                </span>
              </li>
              <li className="flex justify-between gap-2">
                <span className="text-slate-600">IVA cobrado (16%)</span>
                <span className="font-mono font-semibold text-blue-600">
                  ${rf.iva_estimado.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
                </span>
              </li>
              <li className="flex justify-between gap-2 border-t border-slate-100 pt-2">
                <span className="text-slate-800 font-semibold">Ingreso neto</span>
                <span className="font-mono font-bold text-slate-900">
                  ${rf.ingreso_neto.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
                </span>
              </li>
              <li className="flex justify-between gap-2">
                <span className="text-slate-600">Costo de ventas</span>
                <span className="font-mono font-semibold text-amber-600">
                  ${rf.costo_ventas.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
                </span>
              </li>
              <li className="flex justify-between gap-2">
                <span className="text-slate-600">Utilidad bruta</span>
                <span className="font-mono font-semibold text-emerald-600">
                  ${rf.utilidad_bruta.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
                </span>
              </li>
              <li className="flex justify-between gap-2">
                <span className="text-slate-600">Comisiones tarjeta (estim.)</span>
                <span className="font-mono font-semibold text-red-500">
                  ${rf.comisiones_tarjeta.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
                </span>
              </li>
              <li className="flex justify-between gap-2">
                <span className="text-slate-600">Propinas totales</span>
                <span className="font-mono font-semibold text-violet-600">
                  ${rf.propinas_total.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
                </span>
              </li>
            </ul>
          )}
        </SectionCard>
      </div>

      <SectionCard title="Ventas por hora — toda la semana (agrupado por día)">
        {chartHoraSemana.length === 0 ? (
          <p className="text-sm text-slate-500">
            No hay ventas con fecha u hora válidas para armar la matriz hora × día de la semana en este periodo.
          </p>
        ) : (
          <div className="h-80 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartHoraSemana} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="hora" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  tickFormatter={(v) => fmtShortMoney(Number(v))}
                />
                <Tooltip content={<TooltipOscuro />} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {WD_ORDER.map((w) => (
                  <Bar key={w} dataKey={w} name={w} fill={WD_COLORS[w]} radius={[3, 3, 0, 0]} maxBarSize={14} />
                ))}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
