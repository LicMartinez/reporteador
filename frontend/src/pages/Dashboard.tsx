import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import {
  Calendar,
  LayoutDashboard,
  CreditCard,
  Activity,
  ArrowUpRight,
  LogOut,
  Users,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { changePassword, exportTop10Csv, fetchResumen, fetchSucursalesFilter, type Resumen } from '../api/client';
import { format, subDays } from 'date-fns';

function todayISO() {
  return format(new Date(), 'yyyy-MM-dd');
}

function weekStartISO() {
  return format(subDays(new Date(), 7), 'yyyy-MM-dd');
}

const CardStats = ({
  title,
  value,
  trend,
  isPositive,
  icon: Icon,
  prefix = '$',
}: {
  title: string;
  value: number;
  trend?: number;
  isPositive?: boolean;
  icon: typeof Activity;
  prefix?: string;
}) => (
  <div className="card-premium p-6 flex flex-col gap-4">
    <div className="flex justify-between items-start">
      <div>
        <p className="text-sm text-gray-500 font-medium mb-1">{title}</p>
        <h3 className="text-3xl font-bold text-gray-900">
          {prefix}
          {value.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
        </h3>
      </div>
      <div className="p-3 bg-blue-50 rounded-xl">
        <Icon className="w-6 h-6 text-blue-600" />
      </div>
    </div>
    {trend != null && (
      <div className="flex items-center gap-2">
        <span
          className={`flex items-center text-sm font-semibold rounded-full px-2 py-0.5 ${
            isPositive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}
        >
          <ArrowUpRight className="w-4 h-4 mr-1" />
          {trend}%
        </span>
        <span className="text-sm text-gray-500">referencia</span>
      </div>
    )}
  </div>
);

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [range, setRange] = useState<'hoy' | 'semana'>('hoy');
  const [sucursalId, setSucursalId] = useState<string>('');
  const [sucursales, setSucursales] = useState<{ id: string; nombre: string }[]>([]);
  const [data, setData] = useState<Resumen | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Password modal
  const [pwOpen, setPwOpen] = useState(false);
  const [pwOld, setPwOld] = useState('');
  const [pwNew, setPwNew] = useState('');
  const [pwErr, setPwErr] = useState<string | null>(null);

  const { fechaDesde, fechaHasta } = useMemo(() => {
    const hoy = todayISO();
    if (range === 'hoy') return { fechaDesde: hoy, fechaHasta: hoy };
    return { fechaDesde: weekStartISO(), fechaHasta: hoy };
  }, [range]);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [sucs, res] = await Promise.all([
        fetchSucursalesFilter(),
        fetchResumen(fechaDesde, fechaHasta, sucursalId || undefined),
      ]);
      setSucursales(sucs);
      setData(res);
    } catch (e) {
      setErr('No se pudieron cargar los datos. Revisa la API y el token.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [fechaDesde, fechaHasta, sucursalId]);

  useEffect(() => {
    load();
  }, [load]);

  const chartHora = data?.por_hora?.length ? data.por_hora : [{ name: '—', ventas: 0 }];
  const chartMetodo = data?.por_metodo?.length ? data.por_metodo : [{ name: '—', amount: 0 }];

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <aside className="w-72 hidden md:flex flex-col border-r bg-white/70 backdrop-blur-xl p-6 shadow-sm sticky top-0 h-screen">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-800 to-slate-600">
              RestBar Hub
            </h1>
            <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Dashboard</p>
          </div>
        </div>

        <div className="text-sm text-slate-600 mb-6 rounded-xl bg-slate-100/80 p-3">
          <p className="font-semibold text-slate-800">{user?.nombre || user?.email}</p>
          <p className="text-xs mt-1">{user?.is_admin ? 'Administrador' : 'Visor'}</p>
        </div>

        <nav className="flex flex-col gap-2 flex-1">
          <span className="flex items-center gap-3 px-4 py-3 bg-blue-50 text-blue-700 rounded-xl font-semibold">
            <LayoutDashboard className="w-5 h-5" />
            Resumen
          </span>
          {user?.portal_admin && (
            <button
              type="button"
              onClick={() => navigate('/swiss-admin')}
              className="flex items-center gap-3 px-4 py-3 bg-white text-slate-700 hover:bg-slate-50 rounded-xl font-semibold text-left border border-slate-200"
            >
              <Users className="w-5 h-5" />
              Swiss Admin
            </button>
          )}

          <button
            type="button"
            onClick={async () => {
              try {
                const blob = await exportTop10Csv();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'top10_platillos_consolidado.csv';
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
              } catch {
                setErr('No se pudo exportar Top 10.');
              }
            }}
            className="flex items-center gap-3 px-4 py-3 bg-white text-slate-700 hover:bg-slate-50 rounded-xl font-semibold text-left border border-slate-200"
          >
            <LogOut className="w-5 h-5 rotate-180" />
            Exportar Top 10
          </button>

          <button
            type="button"
            onClick={() => {
              setPwOpen(true);
              setPwErr(null);
            }}
            className="flex items-center gap-3 px-4 py-3 bg-white text-slate-700 hover:bg-slate-50 rounded-xl font-semibold text-left border border-slate-200"
          >
            <CreditCard className="w-5 h-5" />
            Cambiar contraseña
          </button>
        </nav>

        <button
          type="button"
          onClick={() => logout()}
          className="mt-4 flex items-center justify-center gap-2 px-4 py-3 text-slate-600 hover:bg-slate-100 rounded-xl font-medium"
        >
          <LogOut className="w-5 h-5" />
          Salir
        </button>
      </aside>

      {pwOpen && (
        <div className="fixed inset-0 z-50 bg-black/30 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200 p-6">
            <h3 className="text-xl font-bold text-slate-800 mb-2">Cambiar contraseña</h3>
            <p className="text-sm text-slate-500 mb-4">Solo se actualiza tu contraseña en el dashboard.</p>

            {pwErr && <p className="mb-3 text-sm text-red-600">{pwErr}</p>}

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Contraseña actual</label>
                <input
                  type="password"
                  value={pwOld}
                  onChange={(e) => setPwOld(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nueva contraseña</label>
                <input
                  type="password"
                  value={pwNew}
                  onChange={(e) => setPwNew(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="mt-5 flex gap-3">
              <button
                type="button"
                className="flex-1 py-3 rounded-xl bg-slate-100 text-slate-800 font-semibold hover:bg-slate-200"
                onClick={() => setPwOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="flex-1 py-3 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700"
                onClick={async () => {
                  setPwErr(null);
                  try {
                    await changePassword(pwOld, pwNew);
                    setPwOpen(false);
                    setPwOld('');
                    setPwNew('');
                  } catch {
                    setPwErr('No se pudo cambiar la contraseña (verifica la actual).');
                  }
                }}
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="flex-1 p-8 md:p-12 overflow-y-auto">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-4">
          <div>
            <h2 className="text-3xl font-bold text-slate-800 tracking-tight">Ventas consolidadas</h2>
            <p className="text-slate-500 mt-1 font-medium">
              Periodo: {fechaDesde} — {fechaHasta}
            </p>
          </div>

          <div className="flex flex-wrap gap-4">
            <select
              className="bg-white border text-sm font-semibold rounded-xl px-4 py-2.5 shadow-sm outline-none focus:ring-2 ring-blue-500 cursor-pointer"
              value={sucursalId}
              onChange={(e) => setSucursalId(e.target.value)}
            >
              <option value="">Todas (según permisos)</option>
              {sucursales.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nombre.replace(/_/g, ' ')}
                </option>
              ))}
            </select>

            <div className="flex items-center gap-2 bg-white border rounded-xl px-4 py-2 shadow-sm">
              <Calendar className="w-5 h-5 text-gray-500" />
              <select
                className="bg-transparent outline-none text-sm font-semibold text-gray-700 cursor-pointer"
                value={range}
                onChange={(e) => setRange(e.target.value as 'hoy' | 'semana')}
              >
                <option value="hoy">Hoy</option>
                <option value="semana">Últimos 7 días</option>
              </select>
            </div>

            <button
              type="button"
              onClick={() => load()}
              className="px-4 py-2 rounded-xl bg-slate-800 text-white text-sm font-semibold hover:bg-slate-900"
            >
              Actualizar
            </button>
          </div>
        </header>

        {err && <p className="mb-6 text-red-600 text-sm">{err}</p>}
        {loading && <p className="mb-6 text-slate-500">Cargando…</p>}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          <CardStats
            title="Ingresos totales"
            value={data?.total_ingresos ?? 0}
            icon={Activity}
          />
          <CardStats
            title="Tickets"
            value={data?.num_tickets ?? 0}
            icon={LayoutDashboard}
            prefix=""
          />
          <CardStats title="Ticket promedio" value={data?.ticket_promedio ?? 0} icon={Users} />
          <CardStats title="Tarjeta (suma slot principal)" value={data?.total_tarjeta ?? 0} icon={CreditCard} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 card-premium p-6">
            <h3 className="text-lg font-bold text-slate-800 mb-6">Ventas por hora (apertura)</h3>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartHora}>
                  <defs>
                    <linearGradient id="colorVentas" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 12 }}
                    dx={-10}
                    tickFormatter={(value) => `$${value}`}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                    formatter={(value) => [`$${value}`, 'Ventas']}
                  />
                  <Area
                    type="monotone"
                    dataKey="ventas"
                    stroke="#4f46e5"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorVentas)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card-premium p-6">
            <h3 className="text-lg font-bold text-slate-800 mb-6">Métodos / tarjetas</h3>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartMetodo} layout="vertical" margin={{ top: 0, right: 0, left: 30, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis type="number" hide />
                  <YAxis
                    dataKey="name"
                    type="category"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#475569', fontSize: 12, fontWeight: 500 }}
                    width={100}
                  />
                  <Tooltip
                    cursor={{ fill: '#f1f5f9' }}
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                    formatter={(value) => [`$${Number(value).toLocaleString('es-MX')}`, 'Monto']}
                  />
                  <Bar dataKey="amount" radius={[0, 6, 6, 0]} barSize={28} fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
