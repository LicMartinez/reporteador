import type { LucideIcon } from 'lucide-react';
import { ArrowDownRight, ArrowUpRight } from 'lucide-react';

const accentStyles = {
  blue: 'border-blue-200 bg-blue-50/80',
  green: 'border-emerald-200 bg-emerald-50/80',
  purple: 'border-violet-200 bg-violet-50/80',
  amber: 'border-amber-200 bg-amber-50/80',
  teal: 'border-teal-200 bg-teal-50/80',
  rose: 'border-rose-200 bg-rose-50/80',
} as const;

const iconAccent = {
  blue: 'bg-blue-500/15 text-blue-700',
  green: 'bg-emerald-500/15 text-emerald-700',
  purple: 'bg-violet-500/15 text-violet-700',
  amber: 'bg-amber-500/15 text-amber-700',
  teal: 'bg-teal-500/15 text-teal-700',
  rose: 'bg-rose-500/15 text-rose-700',
} as const;

export type KpiAccent = keyof typeof accentStyles;

export function KpiCard({
  title,
  value,
  deltaPct,
  icon: Icon,
  prefix = '$',
  monoValue,
  integer,
  accent = 'blue',
  subtitle,
}: {
  title: string;
  value: number;
  deltaPct?: number | null;
  icon: LucideIcon;
  prefix?: string;
  monoValue?: boolean;
  integer?: boolean;
  accent?: KpiAccent;
  subtitle?: string;
}) {
  const showDelta = deltaPct != null && Number.isFinite(deltaPct);
  const positive = (deltaPct ?? 0) >= 0;
  const cardTone = accentStyles[accent];
  const iconTone = iconAccent[accent];

  return (
    <div
      className={`rounded-2xl border-[1.5px] p-5 shadow-sm transition-all duration-150 hover:-translate-y-0.5 hover:shadow-md ${cardTone}`}
    >
      <div className="flex justify-between items-start gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">{title}</p>
          <h3
            className={`text-2xl sm:text-[1.65rem] font-extrabold text-slate-900 tabular-nums leading-tight truncate ${
              monoValue || (!integer && prefix) ? 'font-mono' : ''
            }`}
          >
            {prefix}
            {value.toLocaleString('es-MX', {
              maximumFractionDigits: integer ? 0 : prefix ? 0 : 2,
            })}
          </h3>
          {subtitle ? <p className="text-xs text-slate-500 mt-1.5">{subtitle}</p> : null}
        </div>
        <div className={`shrink-0 p-2.5 rounded-xl ${iconTone}`}>
          <Icon className="w-6 h-6" />
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
