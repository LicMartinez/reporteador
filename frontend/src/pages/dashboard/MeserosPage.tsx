import { UserCircle } from 'lucide-react';
import { SectionCard } from '../../components/dashboard/SectionCard';

export default function MeserosPage() {
  return (
    <SectionCard title="Desempeño por mesero">
      <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
        <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
          <UserCircle className="w-8 h-8 text-slate-400" />
        </div>
        <p className="text-slate-800 font-semibold mb-2">Aún no hay datos de mesero</p>
        <p className="text-slate-600 text-sm max-w-md">
          El modelo de ventas actual no incluye mesero y el agente de sincronización no lo envía. Cuando el POS y el ETL lo
          soporten, esta vista mostrará rankings y métricas.
        </p>
      </div>
    </SectionCard>
  );
}
