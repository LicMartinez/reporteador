import axios from 'axios';
import { clearStoredAuth, getStoredToken, migrateLegacyAuthStorage } from '../lib/authStorage';

const base = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

migrateLegacyAuthStorage();

export const api = axios.create({
  baseURL: base.replace(/\/$/, ''),
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const t = getStoredToken();
  if (t) {
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      clearStoredAuth();
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

export type UserMe = {
  id: string;
  email: string;
  nombre: string | null;
  is_admin: boolean;
  portal_admin: boolean;
  sucursales: { id: string; nombre: string; rol: string | null }[];
};

export type ResumenPorDia = {
  fecha: string;
  total_pagado: number;
  num_tickets: number;
  total_efectivo: number;
  total_tarjeta: number;
};

export type ResumenTopProducto = {
  nombre: string;
  codigo: string | null;
  total_renglon: number;
  cantidad: number;
};

export type ResumenDeltas = {
  total_ingresos_pct: number | null;
  num_tickets_pct: number | null;
  ticket_promedio_pct: number | null;
};

export type Resumen = {
  total_ingresos: number;
  num_tickets: number;
  ticket_promedio: number;
  total_efectivo: number;
  total_tarjeta: number;
  por_hora: { name: string; ventas: number }[];
  por_metodo: { name: string; amount: number }[];
  por_dia: ResumenPorDia[];
  top_productos: ResumenTopProducto[];
  deltas?: ResumenDeltas | null;
};

export type AdminUserBrief = {
  id: string;
  email: string;
  nombre: string | null;
  is_admin: boolean;
  sucursales: { id: string; nombre: string; rol?: string | null }[];
};

// =========================
// Swiss Tools Dashboard Admon
// =========================

export type SwissSucursalBrief = {
  id: string;
  nombre: string;
  last_connection_at?: string | null;
};

export type SwissSucursalLogsItem = {
  id: string;
  tipo?: string | null;
  mensaje?: string | null;
  fecha_registro?: string | null;
  payload_invalido?: Record<string, any> | null;
};

export type SwissCatalogoProductoRule = {
  nombre_maestro: string;
  alias_local: string;
};

export type SwissCatalogoBrief = {
  id: string;
  nombre: string;
  sucursal_ids: string[];
  productos_count: number;
};

export type SwissAdminUserBrief = {
  id: string;
  email: string;
  nombre: string | null;
  dashboard_access_until?: string | null;
  last_dashboard_access_at?: string | null;
  catalogo_maestro_id?: string | null;
  sucursales: { id: string; nombre: string; rol?: string | null }[];
};

export async function fetchSwissSucursales() {
  const { data } = await api.get<SwissSucursalBrief[]>('/swiss-admin/sucursales');
  return data;
}

export async function createSwissSucursal(nombre: string, sync_password: string) {
  const { data } = await api.post<SwissSucursalBrief>('/swiss-admin/sucursales', {
    nombre,
    sync_password,
  });
  return data;
}

export async function fetchSwissSucursalLogs(sucursal_id: string, limit = 50) {
  const { data } = await api.get<SwissSucursalLogsItem[]>(`/swiss-admin/sucursales/${sucursal_id}/logs`, {
    params: { limit },
  });
  return data;
}

export async function fetchSwissDashboardUsers() {
  const { data } = await api.get<SwissAdminUserBrief[]>('/swiss-admin/users');
  return data;
}

export async function createSwissDashboardUser(body: {
  email: string;
  password: string;
  nombre?: string;
  sucursal_ids: string[];
  dashboard_access_until?: string | null;
  catalogo_maestro_id?: string | null;
}) {
  const { data } = await api.post<SwissAdminUserBrief>('/swiss-admin/users', body);
  return data;
}

export async function patchSwissDashboardUserAccess(user_id: string, dashboard_access_until?: string | null) {
  const { data } = await api.patch<SwissAdminUserBrief>(`/swiss-admin/users/${user_id}/access`, {
    dashboard_access_until: dashboard_access_until ?? null,
  });
  return data;
}

export async function fetchSwissCatalogos() {
  const { data } = await api.get<SwissCatalogoBrief[]>('/swiss-admin/catalogos');
  return data;
}

export async function createSwissCatalogo(body: {
  nombre: string;
  sucursal_ids: string[];
  reglas_productos: SwissCatalogoProductoRule[];
}) {
  const { data } = await api.post<SwissCatalogoBrief>('/swiss-admin/catalogos', body);
  return data;
}

export async function updateSwissCatalogo(catalogo_id: string, body: {
  nombre?: string;
  sucursal_ids?: string[] | null;
  reglas_productos?: SwissCatalogoProductoRule[] | null;
}) {
  const { data } = await api.put<SwissCatalogoBrief>(`/swiss-admin/catalogos/${catalogo_id}`, body);
  return data;
}

export async function fetchSwissPortalAdmins() {
  const { data } = await api.get<SwissAdminUserBrief[]>('/swiss-admin/config/admin-users');
  return data;
}

export async function createSwissPortalAdmin(body: { email: string; password: string; nombre?: string }) {
  const { data } = await api.post<SwissAdminUserBrief>('/swiss-admin/config/admin-users', body);
  return data;
}

export async function patchSwissPortalAdmin(user_id: string, body: { email?: string; nombre?: string }) {
  const { data } = await api.patch<SwissAdminUserBrief>(`/swiss-admin/config/admin-users/${user_id}`, body);
  return data;
}

export async function patchSwissPortalAdminPassword(user_id: string, body: { old_password?: string; new_password: string }) {
  const { data } = await api.patch(`/swiss-admin/config/admin-users/${user_id}/password`, body);
  return data;
}

export async function deleteSwissPortalAdmin(user_id: string) {
  const { data } = await api.delete(`/swiss-admin/config/admin-users/${user_id}`);
  return data;
}

export async function login(email: string, password: string) {
  const { data } = await api.post<{ access_token: string; user: UserMe }>('/auth/login', {
    email,
    password,
  });
  return data;
}

export async function fetchMe() {
  const { data } = await api.get<UserMe>('/auth/me');
  return data;
}

export async function fetchResumen(
  fechaDesde: string,
  fechaHasta: string,
  sucursalId?: string,
  opts?: { includePrevious?: boolean }
) {
  const { data } = await api.get<Resumen>('/dashboard/resumen', {
    params: {
      fecha_desde: fechaDesde,
      fecha_hasta: fechaHasta,
      sucursal_id: sucursalId || undefined,
      include_previous: opts?.includePrevious ? true : undefined,
    },
  });
  return data;
}

export async function fetchSucursalesFilter() {
  const { data } = await api.get<{ id: string; nombre: string }[]>('/dashboard/sucursales');
  return data;
}

export async function changePassword(old_password: string, new_password: string) {
  await api.post('/auth/change-password', { old_password, new_password });
}

export async function exportTop10Csv(): Promise<Blob> {
  const { data } = await api.get('/admin/export/top10', { responseType: 'blob' });
  return data as Blob;
}

// =========================
// Admin portal
// =========================

export async function fetchAdminSucursales() {
  const { data } = await api.get<{ id: string; nombre: string }[]>('/admin/sucursales');
  return data;
}

export async function adminCreateSucursal(nombre: string) {
  const { data } = await api.post<{ id: string; nombre: string }>('/admin/sucursales', { nombre });
  return data;
}

export async function fetchAdminUsers() {
  const { data } = await api.get<AdminUserBrief[]>('/admin/users');
  return data;
}

export async function adminCreateUser(body: {
  email: string;
  password: string;
  nombre?: string;
  is_admin: boolean;
  sucursal_ids: string[];
}) {
  const { data } = await api.post<AdminUserBrief>('/admin/users', body);
  return data;
}
