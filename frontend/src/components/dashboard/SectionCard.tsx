import type { ReactNode } from 'react';

export function SectionCard({ title, children, className = '' }: { title: string; children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200/80 bg-white p-6 shadow-sm ${className}`}>
      <h3 className="text-lg font-bold text-slate-900 mb-4">{title}</h3>
      {children}
    </div>
  );
}
