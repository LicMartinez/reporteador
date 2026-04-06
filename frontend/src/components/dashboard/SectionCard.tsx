import type { ReactNode } from 'react';

export function SectionCard({
  title,
  children,
  className = '',
  action,
}: {
  title: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}) {
  return (
    <div className={`rounded-xl border border-slate-200/80 bg-white p-6 shadow-sm ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h3 className="text-lg font-bold text-slate-900">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}
