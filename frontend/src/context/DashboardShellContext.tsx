import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { format, startOfMonth, subDays } from 'date-fns';
import { fetchResumen, fetchSucursalesFilter, type Resumen } from '../api/client';

export type DatePreset = 'hoy' | 'ayer' | '7d' | '30d' | 'este_mes' | 'personalizado';

function computeRange(
  preset: DatePreset,
  customDesde: string,
  customHasta: string
): { fechaDesde: string; fechaHasta: string } {
  const today = new Date();
  const todayStr = format(today, 'yyyy-MM-dd');
  switch (preset) {
    case 'hoy':
      return { fechaDesde: todayStr, fechaHasta: todayStr };
    case 'ayer': {
      const y = format(subDays(today, 1), 'yyyy-MM-dd');
      return { fechaDesde: y, fechaHasta: y };
    }
    case '7d':
      return { fechaDesde: format(subDays(today, 6), 'yyyy-MM-dd'), fechaHasta: todayStr };
    case '30d':
      return { fechaDesde: format(subDays(today, 29), 'yyyy-MM-dd'), fechaHasta: todayStr };
    case 'este_mes':
      return { fechaDesde: format(startOfMonth(today), 'yyyy-MM-dd'), fechaHasta: todayStr };
    case 'personalizado':
      return {
        fechaDesde: customDesde || todayStr,
        fechaHasta: customHasta || todayStr,
      };
    default:
      return { fechaDesde: todayStr, fechaHasta: todayStr };
  }
}

function normalizeResumen(raw: Resumen | null): Resumen | null {
  if (!raw) return null;
  return {
    ...raw,
    por_dia: raw.por_dia ?? [],
    top_productos: raw.top_productos ?? [],
    por_hora: raw.por_hora ?? [],
    por_metodo: raw.por_metodo ?? [],
  };
}

export type DashboardShellValue = {
  preset: DatePreset;
  setPreset: (p: DatePreset) => void;
  customDesde: string;
  customHasta: string;
  setCustomDesde: (s: string) => void;
  setCustomHasta: (s: string) => void;
  fechaDesde: string;
  fechaHasta: string;
  sucursalId: string;
  setSucursalId: (s: string) => void;
  sucursales: { id: string; nombre: string }[];
  data: Resumen | null;
  loading: boolean;
  err: string | null;
  reload: () => void;
};

const DashboardShellContext = createContext<DashboardShellValue | null>(null);

export function DashboardShellProvider({ children }: { children: ReactNode }) {
  const [preset, setPreset] = useState<DatePreset>('hoy');
  const [customDesde, setCustomDesde] = useState(() => format(subDays(new Date(), 6), 'yyyy-MM-dd'));
  const [customHasta, setCustomHasta] = useState(() => format(new Date(), 'yyyy-MM-dd'));
  const [sucursalId, setSucursalId] = useState('');
  const [sucursales, setSucursales] = useState<{ id: string; nombre: string }[]>([]);
  const [data, setData] = useState<Resumen | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const { fechaDesde, fechaHasta } = useMemo(
    () => computeRange(preset, customDesde, customHasta),
    [preset, customDesde, customHasta]
  );

  const reload = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [sucs, res] = await Promise.all([
        fetchSucursalesFilter(),
        fetchResumen(fechaDesde, fechaHasta, sucursalId || undefined, { includePrevious: true }),
      ]);
      setSucursales(sucs);
      setData(normalizeResumen(res));
    } catch {
      setErr('No se pudieron cargar los datos. Revisa la API y el token.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [fechaDesde, fechaHasta, sucursalId]);

  useEffect(() => {
    reload();
  }, [reload]);

  const value = useMemo(
    () => ({
      preset,
      setPreset,
      customDesde,
      customHasta,
      setCustomDesde,
      setCustomHasta,
      fechaDesde,
      fechaHasta,
      sucursalId,
      setSucursalId,
      sucursales,
      data,
      loading,
      err,
      reload,
    }),
    [
      preset,
      customDesde,
      customHasta,
      fechaDesde,
      fechaHasta,
      sucursalId,
      sucursales,
      data,
      loading,
      err,
      reload,
    ]
  );

  return <DashboardShellContext.Provider value={value}>{children}</DashboardShellContext.Provider>;
}

export function useDashboardShell() {
  const ctx = useContext(DashboardShellContext);
  if (!ctx) throw new Error('useDashboardShell fuera de DashboardShellProvider');
  return ctx;
}
