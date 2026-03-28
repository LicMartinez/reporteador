import type { LucideIcon } from 'lucide-react';
import { ArrowDownRight, ArrowUpRight } from 'lucide-react';

export function KpiCard({
  title,
  value,
  deltaPct,
  icon: Icon,
  prefix = '$',
  monoValue,
  integer,
}: {
  title: string;
  value: number;
  deltaPct?: number | null;
  icon: LucideIcon;
  prefix?: string;
  monoValue?: boolean;
  integer?: boolean;
}) {
  const showDelta = deltaPct != null && Number.isFinite(deltaPct);
  const positive = (deltaPct ?? 0) >= 0;

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex justify-between items-start gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-500 mb-1">{title}</p>
          <h3
            className={`text-2xl sm:text-3xl font-bold text-slate-900 tabular-nums truncate ${
              monoValue ? 'font-mono' : ''
            }`}
          >
            {prefix}
            {value.toLocaleString('es-MX', {
              maximumFractionDigits: integer ? 0 : prefix ? 0 : 2,
            })}
          </h3>
        </div>
        <div className="shrink-0 p-3 rounded-xl bg-blue-500/10">
          <Icon className="w-6 h-6 text-blue-600" />
        </div>
      </div>
      {showDelta && (
        <div className="mt-4 flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1 text-xs font-semibold rounded-full px-2 py-0.5 ${
              positive ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
            }`}
          >
            {positive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
            {positive ? '+' : ''}
            {deltaPct}%
          </span>
          <span className="text-xs text-slate-500">vs periodo anterior</span>
        </div>
      )}
    </div>
  );
}
