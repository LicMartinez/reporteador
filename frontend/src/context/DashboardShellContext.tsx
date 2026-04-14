import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { format, startOfMonth, subDays } from 'date-fns';
import { fetchResumen, fetchSucursalesFilter, getApiErrorMessage, type Resumen } from '../api/client';

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
    por_hora_semana: raw.por_hora_semana ?? [],
    por_metodo: raw.por_metodo ?? [],
    por_mesero: raw.por_mesero ?? [],
    por_clase: raw.por_clase ?? [],
    total_costo: raw.total_costo ?? 0,
    utilidad_bruta: raw.utilidad_bruta ?? 0,
    total_propinas: raw.total_propinas ?? 0,
    total_anulaciones_monto: raw.total_anulaciones_monto ?? 0,
  };
}

function sameSet(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const sa = new Set(a);
  return b.every((x) => sa.has(x));
}

function daysBetweenIso(desde: string, hasta: string): number {
  try {
    const d0 = new Date(`${desde}T00:00:00`);
    const d1 = new Date(`${hasta}T00:00:00`);
    const ms = d1.getTime() - d0.getTime();
    return Math.max(1, Math.floor(ms / 86400000) + 1);
  } catch {
    return 1;
  }
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
  selectedSucursalIds: string[];
  setSelectedSucursalIds: (ids: string[] | ((prev: string[]) => string[])) => void;
  toggleSucursalId: (id: string) => void;
  selectAllSucursales: () => void;
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
  const [selectedSucursalIds, setSelectedSucursalIds] = useState<string[]>([]);
  const [sucursales, setSucursales] = useState<{ id: string; nombre: string }[]>([]);
  const [data, setData] = useState<Resumen | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const selectedRef = useRef(selectedSucursalIds);
  selectedRef.current = selectedSucursalIds;
  const prevAllowedSucursalIdsRef = useRef<string[]>([]);

  const { fechaDesde, fechaHasta } = useMemo(
    () => computeRange(preset, customDesde, customHasta),
    [preset, customDesde, customHasta]
  );

  const toggleSucursalId = useCallback((id: string) => {
    setSelectedSucursalIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((x) => x !== id);
      }
      return [...prev, id];
    });
  }, []);

  const selectAllSucursales = useCallback(() => {
    setSelectedSucursalIds(sucursales.map((s) => s.id));
  }, [sucursales]);

  const reload = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const sucs = await fetchSucursalesFilter();
      const allowedIds = sucs.map((s) => s.id);
      setSucursales(sucs);

      const prev = selectedRef.current;
      const prevAllowed = prevAllowedSucursalIdsRef.current;
      const firstSucursalesLoad = prevAllowed.length === 0;

      let next = prev.filter((id) => allowedIds.includes(id));
      const hasPriorManualSelection = prevAllowed.length > 0;
      if (next.length === 0 && allowedIds.length > 0 && !hasPriorManualSelection) {
        next = [...allowedIds];
      } else if (!firstSucursalesLoad) {
        const newlyAdded = allowedIds.filter((id) => !prevAllowed.includes(id));
        for (const id of newlyAdded) {
          if (!next.includes(id)) next.push(id);
        }
      }
      prevAllowedSucursalIdsRef.current = [...allowedIds];
      if (!sameSet(next, prev)) {
        setSelectedSucursalIds(next);
      }

      const allSelected =
        allowedIds.length > 0 &&
        next.length === allowedIds.length &&
        allowedIds.every((id) => next.includes(id));
      const noSelection = next.length === 0;
      const rangeDays = daysBetweenIso(fechaDesde, fechaHasta);
      const includePrevious = rangeDays <= 62;
      const runFetch = () =>
        fetchResumen(fechaDesde, fechaHasta, allSelected ? undefined : next, {
          includePrevious,
          emptySelection: noSelection,
          productosLimit: 1000,
        });
      let res: Resumen;
      try {
        res = await runFetch();
      } catch (err) {
        const msg = getApiErrorMessage(err);
        if (msg.includes('tardó demasiado')) {
          res = await fetchResumen(fechaDesde, fechaHasta, allSelected ? undefined : next, {
            includePrevious: false,
            emptySelection: noSelection,
            productosLimit: 500,
          });
        } else {
          throw err;
        }
      }
      setData(normalizeResumen(res));
    } catch (err) {
      setErr(getApiErrorMessage(err));
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [fechaDesde, fechaHasta, selectedSucursalIds]);

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
      selectedSucursalIds,
      setSelectedSucursalIds,
      toggleSucursalId,
      selectAllSucursales,
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
      selectedSucursalIds,
      toggleSucursalId,
      selectAllSucursales,
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
