import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  CalendarClock,
  KeyRound,
  LogOut,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  createSwissCatalogo,
  createSwissDashboardUser,
  createSwissPortalAdmin,
  createSwissSucursal,
  deleteSwissPortalAdmin,
  fetchSwissCatalogos,
  fetchSwissDashboardUsers,
  fetchSwissPortalAdmins,
  fetchSwissSucursales,
  fetchSwissSucursalLogs,
  patchSwissDashboardUserAccess,
  updateSwissCatalogo,
  patchSwissPortalAdmin,
  patchSwissPortalAdminPassword,
  type SwissCatalogoBrief,
  type SwissCatalogoProductoRule,
  type SwissAdminUserBrief,
  type SwissSucursalBrief,
  type SwissSucursalLogsItem,
} from '../api/client';

type TabKey = 'usuarios' | 'sucursales' | 'catalogos' | 'config';

function isoToDatetimeLocal(iso?: string | null) {
  if (!iso) return '';
  const d = new Date(iso);
  // datetime-local espera "YYYY-MM-DDTHH:mm"
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function datetimeLocalToIso(v: string) {
  if (!v) return null;
  return new Date(v).toISOString();
}

export default function SwissAdminPortal() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();

  const [tab, setTab] = useState<TabKey>('usuarios');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [sucursales, setSucursales] = useState<SwissSucursalBrief[]>([]);
  const [catalogos, setCatalogos] = useState<SwissCatalogoBrief[]>([]);
  const [dashboardUsers, setDashboardUsers] = useState<SwissAdminUserBrief[]>([]);
  const [portalAdmins, setPortalAdmins] = useState<SwissAdminUserBrief[]>([]);

  // Logs (sucursales)
  const [selectedSucursalId, setSelectedSucursalId] = useState<string>('');
  const [logs, setLogs] = useState<SwissSucursalLogsItem[]>([]);

  // Create sucursal
  const [newSucursalNombre, setNewSucursalNombre] = useState('');
  const [newSucursalPassword, setNewSucursalPassword] = useState('');

  // Create dashboard user
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserNombre, setNewUserNombre] = useState('');
  const [newUserAccessUntil, setNewUserAccessUntil] = useState('');
  const [newUserCatalogoId, setNewUserCatalogoId] = useState<string | null>(null);
  const [newUserSucursalIds, setNewUserSucursalIds] = useState<string[]>([]);

  // Create portal admin
  const [newPortalAdminEmail, setNewPortalAdminEmail] = useState('');
  const [newPortalAdminPassword, setNewPortalAdminPassword] = useState('');
  const [newPortalAdminNombre, setNewPortalAdminNombre] = useState('');

  // Create/update catalog rules
  const [catalogoFormNombre, setCatalogoFormNombre] = useState('');
  const [catalogoFormSucursalIds, setCatalogoFormSucursalIds] = useState<string[]>([]);
  const [catalogoFormRules, setCatalogoFormRules] = useState<SwissCatalogoProductoRule[]>([]);
  const [catalogoEditingId, setCatalogoEditingId] = useState<string | null>(null);
  const [ruleNombreMaestro, setRuleNombreMaestro] = useState('');
  const [ruleAliasLocal, setRuleAliasLocal] = useState('');

  const loadAll = useCallback(async () => {
    setErr(null);
    setBusy(true);
    try {
      const [sucs, cats, users, admins] = await Promise.all([
        fetchSwissSucursales(),
        fetchSwissCatalogos(),
        fetchSwissDashboardUsers(),
        fetchSwissPortalAdmins(),
      ]);
      setSucursales(sucs);
      setCatalogos(cats);
      setDashboardUsers(users);
      setPortalAdmins(admins);
    } catch {
      setErr('No se pudieron cargar los datos del portal.');
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!loading && user?.portal_admin) {
      loadAll();
    }
  }, [loading, user?.portal_admin, loadAll]);

  useEffect(() => {
    if (selectedSucursalId) {
      fetchSwissSucursalLogs(selectedSucursalId, 50)
        .then(setLogs)
        .catch(() => setLogs([]));
    } else {
      setLogs([]);
    }
  }, [selectedSucursalId]);

  const canCreateUser = useMemo(() => {
    return newUserEmail.trim() && newUserPassword.trim() && newUserSucursalIds.length > 0;
  }, [newUserEmail, newUserPassword, newUserSucursalIds]);

  async function onCreateSucursal(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await createSwissSucursal(newSucursalNombre.trim().toUpperCase(), newSucursalPassword);
      setNewSucursalNombre('');
      setNewSucursalPassword('');
      await loadAll();
    } catch {
      setErr('No se pudo crear la sucursal. Revisa nombre y contraseña.');
    } finally {
      setBusy(false);
    }
  }

  async function onCreateDashboardUser(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await createSwissDashboardUser({
        email: newUserEmail.trim(),
        password: newUserPassword,
        nombre: newUserNombre.trim() || undefined,
        sucursal_ids: newUserSucursalIds,
        dashboard_access_until: datetimeLocalToIso(newUserAccessUntil),
        catalogo_maestro_id: newUserCatalogoId,
      });
      setNewUserEmail('');
      setNewUserPassword('');
      setNewUserNombre('');
      setNewUserAccessUntil('');
      setNewUserCatalogoId(null);
      setNewUserSucursalIds([]);
      await loadAll();
    } catch {
      setErr('No se pudo crear el usuario. Revisa email, sucursales y fecha.');
    } finally {
      setBusy(false);
    }
  }

  async function onUpdateUserAccess(userId: string, accessUntilLocal: string) {
    setBusy(true);
    setErr(null);
    try {
      const iso = datetimeLocalToIso(accessUntilLocal);
      await patchSwissDashboardUserAccess(userId, iso);
      await loadAll();
    } catch {
      setErr('No se pudo actualizar la fecha de acceso.');
    } finally {
      setBusy(false);
    }
  }

  async function onCreatePortalAdmin(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await createSwissPortalAdmin({
        email: newPortalAdminEmail.trim(),
        password: newPortalAdminPassword,
        nombre: newPortalAdminNombre.trim() || undefined,
      });
      setNewPortalAdminEmail('');
      setNewPortalAdminPassword('');
      setNewPortalAdminNombre('');
      await loadAll();
    } catch {
      setErr('No se pudo crear el administrador del portal.');
    } finally {
      setBusy(false);
    }
  }

  async function onChangePortalAdminPassword(userId: string, newPassword: string) {
    setBusy(true);
    setErr(null);
    try {
      await patchSwissPortalAdminPassword(userId, { new_password: newPassword });
      await loadAll();
    } catch {
      setErr('No se pudo cambiar la contraseña del portal.');
    } finally {
      setBusy(false);
    }
  }

  async function onDeletePortalAdmin(userId: string) {
    setBusy(true);
    setErr(null);
    try {
      await deleteSwissPortalAdmin(userId);
      await loadAll();
    } catch {
      setErr('No se pudo eliminar el administrador del portal.');
    } finally {
      setBusy(false);
    }
  }

  function addRule() {
    const maestro = ruleNombreMaestro.trim();
    const alias = ruleAliasLocal.trim().toUpperCase();
    if (!maestro || !alias) return;
    setCatalogoFormRules((prev) => [...prev, { nombre_maestro: maestro, alias_local: alias }]);
    setRuleNombreMaestro('');
    setRuleAliasLocal('');
  }

  async function onSubmitCatalogo(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const payload = {
        nombre: catalogoFormNombre.trim(),
        sucursal_ids: catalogoFormSucursalIds,
        reglas_productos: catalogoFormRules,
      };
      if (catalogoEditingId) {
        await updateSwissCatalogo(catalogoEditingId, payload);
      } else {
        await createSwissCatalogo(payload);
      }
      setCatalogoFormNombre('');
      setCatalogoFormSucursalIds([]);
      setCatalogoFormRules([]);
      setCatalogoEditingId(null);
      await loadAll();
    } catch {
      setErr('No se pudo crear el catálogo maestro.');
    } finally {
      setBusy(false);
    }
  }

  if (loading || busy && !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 text-slate-600">Cargando…</div>
    );
  }

  if (!user) {
    navigate('/login');
    return null;
  }

  if (!user.portal_admin) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-8">
        <div className="max-w-lg w-full bg-white rounded-2xl shadow-sm border p-7">
          <div className="flex items-center gap-3 mb-4">
            <ShieldCheck className="w-6 h-6 text-red-600" />
            <h1 className="text-xl font-bold text-slate-900">Acceso restringido</h1>
          </div>
          <p className="text-slate-600">Tu cuenta no es administrador del portal.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <aside className="w-72 hidden md:flex flex-col border-r bg-white/70 backdrop-blur-xl p-6 shadow-sm sticky top-0 h-screen">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30">
            <KeyRound className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-800 to-slate-600">
              RestBar Hub
            </h1>
            <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Swiss Tools Admon</p>
          </div>
        </div>

        <div className="text-sm text-slate-600 mb-6 rounded-xl bg-slate-100/80 p-3">
          <p className="font-semibold text-slate-800">{user?.nombre || user?.email}</p>
          <p className="text-xs mt-1">Portal admin</p>
        </div>

        <nav className="flex flex-col gap-2 flex-1">
          <button
            type="button"
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-semibold text-left ${
              tab === 'usuarios' ? 'bg-blue-50 text-blue-700' : 'hover:bg-slate-100 text-slate-700 bg-transparent'
            }`}
            onClick={() => setTab('usuarios')}
          >
            <Users className="w-5 h-5" />
            Usuarios
          </button>

          <button
            type="button"
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-semibold text-left ${
              tab === 'sucursales' ? 'bg-blue-50 text-blue-700' : 'hover:bg-slate-100 text-slate-700 bg-transparent'
            }`}
            onClick={() => setTab('sucursales')}
          >
            <Building2 className="w-5 h-5" />
            Sucursales
          </button>

          <button
            type="button"
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-semibold text-left ${
              tab === 'catalogos' ? 'bg-blue-50 text-blue-700' : 'hover:bg-slate-100 text-slate-700 bg-transparent'
            }`}
            onClick={() => setTab('catalogos')}
          >
            <CalendarClock className="w-5 h-5" />
            Catálogos maestros
          </button>

          <button
            type="button"
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-semibold text-left ${
              tab === 'config' ? 'bg-blue-50 text-blue-700' : 'hover:bg-slate-100 text-slate-700 bg-transparent'
            }`}
            onClick={() => setTab('config')}
          >
            <ShieldCheck className="w-5 h-5" />
            Configuración
          </button>
        </nav>

        <button
          type="button"
          onClick={() => {
            logout();
            navigate('/login');
          }}
          className="mt-4 flex items-center justify-center gap-2 px-4 py-3 text-slate-600 hover:bg-slate-100 rounded-xl font-medium"
        >
          <LogOut className="w-5 h-5" />
          Salir
        </button>
      </aside>

      <main className="flex-1 p-8 md:p-12 overflow-y-auto">
        {err && <p className="mb-4 text-red-600 text-sm">{err}</p>}
        {busy && <p className="mb-4 text-slate-500 text-sm">Procesando…</p>}

        {tab === 'sucursales' && (
          <div>
            <h2 className="text-3xl font-bold text-slate-800 tracking-tight mb-2">Sucursales</h2>
            <p className="text-slate-500 mb-6">Crea sucursales con su contraseña y consulta conexión/logs.</p>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section className="card-premium p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Crear sucursal</h3>
                <form onSubmit={onCreateSucursal} className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">ID sucursal (nombre)</label>
                    <input
                      value={newSucursalNombre}
                      onChange={(e) => setNewSucursalNombre(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Ej: PANEM_QUERETARO"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Contraseña sync</label>
                    <input
                      value={newSucursalPassword}
                      onChange={(e) => setNewSucursalPassword(e.target.value)}
                      type="password"
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Contraseña"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full py-3 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-60 transition"
                    disabled={busy}
                  >
                    Crear
                  </button>
                </form>
              </section>

              <section className="card-premium p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Listado</h3>
                <div className="space-y-3">
                  {sucursales.map((s) => (
                    <div key={s.id} className="border border-slate-200 rounded-xl p-3 flex items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-800">{s.nombre.replace(/_/g, ' ')}</p>
                        <p className="text-xs text-slate-500">
                          Última conexión: {s.last_connection_at ? new Date(s.last_connection_at).toLocaleString() : '—'}
                        </p>
                      </div>
                      <div>
                        <button
                          type="button"
                          onClick={() => setSelectedSucursalId(s.id)}
                          className="px-3 py-2 rounded-xl bg-slate-800 text-white text-sm font-semibold hover:bg-slate-900"
                        >
                          Ver logs
                        </button>
                      </div>
                    </div>
                  ))}
                  {!sucursales.length && <p className="text-sm text-slate-500">No hay sucursales.</p>}
                </div>

                {selectedSucursalId && (
                  <div className="mt-6">
                    <h4 className="text-sm font-semibold text-slate-800 mb-2">Logs recientes</h4>
                    <div className="max-h-64 overflow-y-auto rounded-xl border border-slate-200 p-3 bg-white">
                      {!logs.length && <p className="text-sm text-slate-500">Sin logs.</p>}
                      {logs.map((l) => (
                        <div key={l.id} className="border-t border-slate-100 pt-2 mt-2">
                          <p className="text-xs text-slate-600 font-semibold">{l.tipo || '—'}</p>
                          <p className="text-sm text-slate-800 break-words">{l.mensaje || '—'}</p>
                          <p className="text-xs text-slate-500">
                            {l.fecha_registro ? new Date(l.fecha_registro).toLocaleString() : ''}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            </div>
          </div>
        )}

        {tab === 'usuarios' && (
          <div>
            <h2 className="text-3xl font-bold text-slate-800 tracking-tight mb-2">Usuarios (dashboard)</h2>
            <p className="text-slate-500 mb-6">Control de acceso por fecha y asignación de sucursales + catálogo maestro.</p>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section className="card-premium p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Crear usuario</h3>
                <form onSubmit={onCreateDashboardUser} className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                      <input
                        value={newUserEmail}
                        onChange={(e) => setNewUserEmail(e.target.value)}
                        type="email"
                        className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Nombre (opcional)</label>
                      <input
                        value={newUserNombre}
                        onChange={(e) => setNewUserNombre(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Contraseña</label>
                    <input
                      value={newUserPassword}
                      onChange={(e) => setNewUserPassword(e.target.value)}
                      type="password"
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Acceso hasta</label>
                    <input
                      type="datetime-local"
                      value={newUserAccessUntil}
                      onChange={(e) => setNewUserAccessUntil(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-slate-500 mt-1">Vacío = no expira (por defecto).</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Catálogo maestro (opcional)</label>
                    <select
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                      value={newUserCatalogoId ?? ''}
                      onChange={(e) => setNewUserCatalogoId(e.target.value || null)}
                    >
                      <option value="">Sin catálogo maestro</option>
                      {catalogos.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Acceso a sucursales</label>
                    <div className="max-h-44 overflow-y-auto rounded-xl border border-slate-200 p-3 bg-white">
                      {sucursales.map((s) => (
                        <label key={s.id} className="flex items-center gap-2 py-1.5 text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={newUserSucursalIds.includes(s.id)}
                            onChange={(e) => {
                              if (e.target.checked) setNewUserSucursalIds((prev) => [...prev, s.id]);
                              else setNewUserSucursalIds((prev) => prev.filter((x) => x !== s.id));
                            }}
                          />
                          <span>{s.nombre.replace(/_/g, ' ')}</span>
                        </label>
                      ))}
                      {!sucursales.length && <p className="text-sm text-slate-500">Crea sucursales primero.</p>}
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="w-full py-3 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-60 transition"
                    disabled={busy || !canCreateUser}
                  >
                    Crear usuario
                  </button>
                </form>
              </section>

              <section className="card-premium p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Consultar usuarios</h3>
                <div className="space-y-3">
                  {dashboardUsers.map((u) => (
                    <div key={u.id} className="border border-slate-200 rounded-xl p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-slate-800">{u.email}</p>
                          <p className="text-xs text-slate-500">
                            Acceso hasta: {u.dashboard_access_until ? new Date(u.dashboard_access_until).toLocaleString() : '—'}
                          </p>
                        </div>
                        <div className="text-xs text-slate-500">Sucursales: {u.sucursales.length}</div>
                      </div>

                      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 items-end">
                        <div>
                          <label className="block text-xs font-medium text-slate-600 mb-1">Modificar acceso</label>
                          <input
                            id={`accessInput-${u.id}`}
                            type="datetime-local"
                            defaultValue={isoToDatetimeLocal(u.dashboard_access_until)}
                            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                        <div>
                          <button
                            type="button"
                            className="w-full py-2 rounded-xl bg-slate-800 text-white text-sm font-semibold hover:bg-slate-900"
                            onClick={async () => {
                              // Re-read from input in this row using querySelector.
                              const input = document.getElementById(`accessInput-${u.id}`) as HTMLInputElement | null;
                              const val = input?.value || '';
                              await onUpdateUserAccess(u.id, val);
                            }}
                          >
                            Guardar
                          </button>
                        </div>
                      </div>

                    </div>
                  ))}
                  {!dashboardUsers.length && <p className="text-sm text-slate-500">No hay usuarios.</p>}
                </div>
              </section>
            </div>
          </div>
        )}

        {tab === 'catalogos' && (
          <div>
            <h2 className="text-3xl font-bold text-slate-800 tracking-tight mb-2">Catálogos maestros</h2>
            <p className="text-slate-500 mb-6">Alias locales -> nombre maestro para fuzzy matching.</p>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section className="card-premium p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Crear catálogo</h3>
                <form onSubmit={onSubmitCatalogo} className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Modo</label>
                    <select
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                      value={catalogoEditingId ?? ''}
                      onChange={(e) => {
                        const v = e.target.value || null;
                        setCatalogoEditingId(v);
                      }}
                    >
                      <option value="">Crear nuevo</option>
                      {catalogos.map((c) => (
                        <option key={c.id} value={c.id}>
                          Editar: {c.nombre}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Nombre catálogo maestro</label>
                    <input
                      value={catalogoFormNombre}
                      onChange={(e) => setCatalogoFormNombre(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Sucursales que comparten este catálogo</label>
                    <div className="max-h-36 overflow-y-auto rounded-xl border border-slate-200 p-3 bg-white">
                      {sucursales.map((s) => (
                        <label key={s.id} className="flex items-center gap-2 py-1.5 text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={catalogoFormSucursalIds.includes(s.id)}
                            onChange={(e) => {
                              if (e.target.checked) setCatalogoFormSucursalIds((prev) => [...prev, s.id]);
                              else setCatalogoFormSucursalIds((prev) => prev.filter((x) => x !== s.id));
                            }}
                          />
                          <span>{s.nombre.replace(/_/g, ' ')}</span>
                        </label>
                      ))}
                      {!sucursales.length && <p className="text-sm text-slate-500">Crea sucursales primero.</p>}
                    </div>
                  </div>

                  <div className="border-t border-slate-200 pt-4">
                    <h4 className="text-sm font-semibold text-slate-800 mb-2">Reglas fuzzy</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">Nombre maestro</label>
                        <input
                          value={ruleNombreMaestro}
                          onChange={(e) => setRuleNombreMaestro(e.target.value)}
                          className="w-full rounded-xl border border-slate-200 px-3 py-2 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">Alias local</label>
                        <input
                          value={ruleAliasLocal}
                          onChange={(e) => setRuleAliasLocal(e.target.value)}
                          className="w-full rounded-xl border border-slate-200 px-3 py-2 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                    <button type="button" className="mt-2 px-3 py-2 rounded-xl bg-slate-800 text-white text-sm font-semibold hover:bg-slate-900" onClick={addRule}>
                      Agregar regla
                    </button>

                    <div className="mt-3 max-h-40 overflow-y-auto rounded-xl border border-slate-200 p-3 bg-white">
                      {catalogoFormRules.map((r, idx) => (
                        <div key={`${r.nombre_maestro}-${r.alias_local}-${idx}`} className="flex items-center justify-between gap-3 py-1.5 border-t border-slate-100 first:border-t-0">
                          <div>
                            <p className="text-xs text-slate-500">Alias: {r.alias_local}</p>
                            <p className="text-sm font-semibold text-slate-800">{r.nombre_maestro}</p>
                          </div>
                          <button
                            type="button"
                            className="text-xs font-semibold text-red-700 hover:text-red-800"
                            onClick={() => setCatalogoFormRules((prev) => prev.filter((_, i) => i !== idx))}
                          >
                            Quitar
                          </button>
                        </div>
                      ))}
                      {!catalogoFormRules.length && <p className="text-sm text-slate-500">Agrega reglas para el fuzzy matching.</p>}
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="w-full py-3 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-60 transition"
                    disabled={busy}
                  >
                      {catalogoEditingId ? 'Guardar cambios' : 'Crear catálogo'}
                  </button>
                </form>
              </section>

              <section className="card-premium p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Listado</h3>
                <div className="space-y-3">
                  {catalogos.map((c) => (
                    <div key={c.id} className="border border-slate-200 rounded-xl p-3">
                      <p className="font-semibold text-slate-800">{c.nombre}</p>
                      <p className="text-xs text-slate-500">Reglas: {c.productos_count}</p>
                      <p className="text-xs text-slate-500">
                        Sucursales: {c.sucursal_ids.length}
                      </p>
                    </div>
                  ))}
                  {!catalogos.length && <p className="text-sm text-slate-500">Aún no hay catálogos.</p>}
                </div>
              </section>
            </div>
          </div>
        )}

        {tab === 'config' && (
          <div>
            <h2 className="text-3xl font-bold text-slate-800 tracking-tight mb-2">Configuración</h2>
            <p className="text-slate-500 mb-6">Administradores del portal (Swiss Tools Dashboard Admon).</p>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section className="card-premium p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Crear admin portal</h3>
                <form onSubmit={onCreatePortalAdmin} className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                    <input
                      value={newPortalAdminEmail}
                      onChange={(e) => setNewPortalAdminEmail(e.target.value)}
                      type="email"
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Nombre (opcional)</label>
                    <input
                      value={newPortalAdminNombre}
                      onChange={(e) => setNewPortalAdminNombre(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Contraseña</label>
                    <input
                      value={newPortalAdminPassword}
                      onChange={(e) => setNewPortalAdminPassword(e.target.value)}
                      type="password"
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full py-3 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-60 transition"
                    disabled={busy}
                  >
                    Crear admin
                  </button>
                </form>
              </section>

              <section className="card-premium p-6">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Admin portal existentes</h3>
                <div className="space-y-3">
                  {portalAdmins.map((a) => (
                    <div key={a.id} className="border border-slate-200 rounded-xl p-3">
                      <p className="font-semibold text-slate-800">{a.email}</p>
                      <p className="text-xs text-slate-500">{a.nombre || '—'}</p>

                      <div className="mt-3 flex flex-wrap gap-3 items-end">
                        <input
                          className="flex-1 min-w-[220px] rounded-xl border border-slate-200 px-3 py-2 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                          defaultValue={a.nombre || ''}
                          id={`edit-name-${a.id}`}
                          placeholder="Nombre (editar)"
                        />
                        <input
                          className="flex-1 min-w-[240px] rounded-xl border border-slate-200 px-3 py-2 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                          defaultValue={a.email}
                          id={`edit-email-${a.id}`}
                          placeholder="Email (editar)"
                        />
                        <input
                          className="flex-1 min-w-[180px] rounded-xl border border-slate-200 px-3 py-2 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500"
                          type="password"
                          placeholder="Nueva contraseña"
                          id={`pw-${a.id}`}
                        />
                        <button
                          type="button"
                          className="px-4 py-2 rounded-xl bg-slate-800 text-white text-sm font-semibold hover:bg-slate-900"
                          onClick={() => {
                            const el = document.getElementById(`pw-${a.id}`) as HTMLInputElement | null;
                            const val = el?.value || '';
                            if (!val) return;
                            onChangePortalAdminPassword(a.id, val);
                          }}
                        >
                          Cambiar password
                        </button>
                        <button
                          type="button"
                          className="px-3 py-2 rounded-xl bg-indigo-700 text-white text-sm font-semibold hover:bg-indigo-800"
                          onClick={async () => {
                            const nameEl = document.getElementById(`edit-name-${a.id}`) as HTMLInputElement | null;
                            const emailEl = document.getElementById(`edit-email-${a.id}`) as HTMLInputElement | null;
                            const nombre = nameEl?.value || '';
                            const email = emailEl?.value || '';
                            if (!email) return;
                            await patchSwissPortalAdmin(a.id, { email, nombre: nombre || undefined });
                            await loadAll();
                          }}
                        >
                          Guardar datos
                        </button>
                        <button
                          type="button"
                          className="px-3 py-2 rounded-xl bg-red-600 text-white text-sm font-semibold hover:bg-red-700"
                          onClick={() => onDeletePortalAdmin(a.id)}
                        >
                          Eliminar
                        </button>
                      </div>
                    </div>
                  ))}
                  {!portalAdmins.length && <p className="text-sm text-slate-500">No hay administradores del portal.</p>}
                </div>
              </section>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

