import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Building2, ShieldCheck, KeyRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  adminCreateSucursal,
  adminCreateUser,
  fetchAdminSucursales,
  fetchAdminUsers,
  type AdminUserBrief,
} from '../api/client';

type Sucursal = { id: string; nombre: string };

export default function AdminPortal() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [adminUsers, setAdminUsers] = useState<AdminUserBrief[]>([]);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Forms: sucursales
  const [nuevoSucursalNombre, setNuevoSucursalNombre] = useState('');

  // Forms: usuarios
  const [email, setEmail] = useState('');
  const [nombre, setNombre] = useState('');
  const [password, setPassword] = useState('');
  const [isAdminNuevo, setIsAdminNuevo] = useState(false);
  const [sucursalIds, setSucursalIds] = useState<string[]>([]);

  const allSelected = useMemo(() => {
    if (!sucursales.length) return false;
    return sucursalIds.length === sucursales.length;
  }, [sucursales, sucursalIds]);

  const loadAll = useCallback(async () => {
    setErr(null);
    setBusy(true);
    try {
      const [sucs, users] = await Promise.all([fetchAdminSucursales(), fetchAdminUsers()]);
      setSucursales(sucs);
      setAdminUsers(users);
    } catch (e: any) {
      setErr('No se pudieron cargar los datos del admin.');
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (user?.is_admin) loadAll();
  }, [user?.is_admin, loadAll]);

  async function onCreateSucursal(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const nombreNorm = nuevoSucursalNombre.trim().toUpperCase();
      await adminCreateSucursal(nombreNorm);
      setNuevoSucursalNombre('');
      await loadAll();
    } catch (e: any) {
      setErr('No se pudo crear la sucursal (revisa que no exista).');
    } finally {
      setBusy(false);
    }
  }

  async function onCreateUser(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const payload = {
        email,
        password,
        nombre: nombre.trim() || undefined,
        is_admin: isAdminNuevo,
        sucursal_ids: sucursalIds,
      };
      await adminCreateUser(payload);
      // Reset parcial (password por seguridad)
      setPassword('');
      setEmail('');
      setNombre('');
      setIsAdminNuevo(false);
      setSucursalIds([]);
      await loadAll();
    } catch (e: any) {
      setErr('No se pudo crear el usuario. Revisa email y sucursales.');
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 text-slate-600">
        Cargando…
      </div>
    );
  }

  if (!user) {
    navigate('/login');
    return null;
  }

  if (!user.is_admin) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-8">
        <div className="max-w-lg w-full bg-white rounded-2xl shadow-sm border p-7">
          <div className="flex items-center gap-3 mb-4">
            <ShieldCheck className="w-6 h-6 text-red-600" />
            <h1 className="text-xl font-bold text-slate-900">Acceso restringido</h1>
          </div>
          <p className="text-slate-600">
            Tu cuenta no tiene permisos de administrador para gestionar usuarios y sucursales.
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="mt-5 w-full py-2.5 rounded-xl bg-slate-800 text-white font-semibold hover:bg-slate-900"
          >
            Volver al dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <aside className="w-72 hidden md:flex flex-col border-r bg-white/70 backdrop-blur-xl p-6 shadow-sm sticky top-0 h-screen">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30">
            <KeyRound className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-800 to-slate-600">
              RestBar Hub
            </h1>
            <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Admin</p>
          </div>
        </div>

        <div className="text-sm text-slate-600 mb-6 rounded-xl bg-slate-100/80 p-3">
          <p className="font-semibold text-slate-800">{user?.nombre || user?.email}</p>
          <p className="text-xs mt-1">Administrador</p>
        </div>

        <button
          type="button"
          onClick={() => navigate('/')}
          className="mt-auto flex items-center gap-3 px-4 py-3 bg-slate-50 hover:bg-slate-100 rounded-xl font-semibold text-slate-800"
        >
          <Users className="w-5 h-5" />
          Dashboard
        </button>
      </aside>

      <main className="flex-1 p-8 md:p-12 overflow-y-auto">
        <header className="mb-6">
          <h2 className="text-3xl font-bold text-slate-800 tracking-tight">Portal administrativo</h2>
          <p className="text-slate-500 mt-2">
            Crea sucursales y usuarios para que puedan acceder al dashboard por permisos.
          </p>
        </header>

        {err && <p className="mb-4 text-red-600 text-sm">{err}</p>}
        {busy && <p className="mb-4 text-slate-500 text-sm">Procesando…</p>}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="card-premium p-6">
            <div className="flex items-center gap-3 mb-4">
              <Building2 className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-bold text-slate-800">1) Crear sucursal</h3>
            </div>
            <form onSubmit={onCreateSucursal} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nombre</label>
                <input
                  value={nuevoSucursalNombre}
                  onChange={(e) => setNuevoSucursalNombre(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Ej: BAR_LOVE"
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-60 transition"
                disabled={busy}
              >
                Crear sucursal
              </button>
            </form>

            <div className="mt-6">
              <h4 className="text-sm font-semibold text-slate-800 mb-3">Sucursales existentes</h4>
              <div className="flex flex-wrap gap-2">
                {sucursales.map((s) => (
                  <span key={s.id} className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-sm">
                    {s.nombre.replace(/_/g, ' ')}
                  </span>
                ))}
                {!sucursales.length && <p className="text-sm text-slate-500">Aún no hay sucursales.</p>}
              </div>
            </div>
          </section>

          <section className="card-premium p-6">
            <div className="flex items-center gap-3 mb-4">
              <Users className="w-5 h-5 text-blue-600" />
              <h3 className="text-lg font-bold text-slate-800">2) Crear usuario</h3>
            </div>

            <form onSubmit={onCreateUser} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                  <input
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    type="email"
                    className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Nombre</label>
                  <input
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="(opcional)"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Contraseña</label>
                <input
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  type="password"
                  className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <p className="text-xs text-slate-500 mt-1">Se guarda como hash en la base de datos.</p>
              </div>

              <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">
                <input
                  type="checkbox"
                  checked={isAdminNuevo}
                  onChange={(e) => setIsAdminNuevo(e.target.checked)}
                  id="isAdminNuevo"
                />
                <label htmlFor="isAdminNuevo" className="text-sm font-semibold text-slate-800">
                  Administrador del portal (acceso a /admin)
                </label>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-slate-700">Acceso a sucursales</label>
                  <button
                    type="button"
                    className="text-xs font-semibold text-blue-700 hover:text-blue-800"
                    onClick={() => {
                      if (allSelected) setSucursalIds([]);
                      else setSucursalIds(sucursales.map((s) => s.id));
                    }}
                  >
                    {allSelected ? 'Quitar todo' : 'Seleccionar todo'}
                  </button>
                </div>

                <div className="max-h-44 overflow-y-auto rounded-xl border border-slate-200 p-3 bg-white">
                  {sucursales.map((s) => (
                    <label key={s.id} className="flex items-center gap-2 py-1.5 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={sucursalIds.includes(s.id)}
                        onChange={(e) => {
                          if (e.target.checked) setSucursalIds((prev) => [...prev, s.id]);
                          else setSucursalIds((prev) => prev.filter((x) => x !== s.id));
                        }}
                      />
                      <span>{s.nombre.replace(/_/g, ' ')}</span>
                    </label>
                  ))}
                  {!sucursales.length && (
                    <p className="text-sm text-slate-500">Primero crea sucursales.</p>
                  )}
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-slate-800 text-white font-semibold hover:bg-slate-900 disabled:opacity-60 transition"
                disabled={busy}
              >
                Crear usuario
              </button>
            </form>
          </section>
        </div>

        <section className="card-premium p-6 mt-6">
          <h3 className="text-lg font-bold text-slate-800 mb-4">Usuarios existentes</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-slate-500">
                <tr className="text-left">
                  <th className="pb-2 font-semibold">Email</th>
                  <th className="pb-2 font-semibold">Nombre</th>
                  <th className="pb-2 font-semibold">Admin portal</th>
                  <th className="pb-2 font-semibold">Sucursales</th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                {adminUsers.map((u) => (
                  <tr key={u.id} className="border-t border-slate-200">
                    <td className="py-3 pr-3">{u.email}</td>
                    <td className="py-3 pr-3">{u.nombre || '-'}</td>
                    <td className="py-3 pr-3">{u.is_admin ? 'Sí' : 'No'}</td>
                    <td className="py-3">
                      <div className="flex flex-wrap gap-2">
                        {u.sucursales.map((s) => (
                          <span
                            key={s.id}
                            className="px-2 py-1 rounded-full bg-slate-100 text-slate-700 text-xs"
                          >
                            {s.nombre.replace(/_/g, ' ')}
                          </span>
                        ))}
                        {!u.sucursales.length && <span className="text-slate-500">—</span>}
                      </div>
                    </td>
                  </tr>
                ))}
                {!adminUsers.length && (
                  <tr>
                    <td className="py-5 text-slate-500" colSpan={4}>
                      No hay usuarios aún.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

