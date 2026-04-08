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
  if (config.data instanceof FormData) {
    delete (config.headers as Record<string, unknown>)['Content-Type'];
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
  total_costo?: number;
};

export type ResumenTopProducto = {
  nombre: string;
  codigo?: string | null;
  /** 1=BEBIDAS, 2=ALIMENTOS, 3=OTROS (según renglón dominante). */
  clase?: number;
  total_renglon: number;
  cantidad: number;
  total_costo?: number;
  margen_pct?: number | null;
};

export type ResumenDeltas = {
  total_ingresos_pct: number | null;
  num_tickets_pct: number | null;
  ticket_promedio_pct: number | null;
  total_costo_pct?: number | null;
  utilidad_bruta_pct?: number | null;
  total_propinas_pct?: number | null;
};

export type ResumenMesero = {
  nombre: string;
  sucursales: string[];
  total_pagado: number;
  num_tickets: number;
  propinas?: number;
  ticket_promedio?: number;
};

export type ResumenClase = {
  name: string;
  clase_key: number;
  total_renglon: number;
  cantidad: number;
};

export type ResumenFinanciero = {
  ingreso_bruto: number;
  iva_estimado: number;
  ingreso_neto: number;
  costo_ventas: number;
  utilidad_bruta: number;
  comisiones_tarjeta: number;
  propinas_total: number;
};

export type ComisionesEstimadas = {
  total_comision: number;
  base_tarjeta: number;
  detalle: { metodo: string; monto: number; tasa_pct: number; comision: number }[];
};

export type ResumenPorHoraSemana = {
  hora: string;
  Lun?: number;
  Mar?: number;
  Mié?: number;
  Jue?: number;
  Vie?: number;
  Sáb?: number;
  Dom?: number;
};

export type Resumen = {
  total_ingresos: number;
  num_tickets: number;
  ticket_promedio: number;
  total_efectivo: number;
  total_tarjeta: number;
  total_costo?: number;
  utilidad_bruta?: number;
  margen_pct?: number | null;
  total_propinas?: number;
  total_anulaciones_monto?: number;
  por_hora: { name: string; ventas: number }[];
  por_hora_semana?: ResumenPorHoraSemana[];
  por_metodo: { name: string; amount: number }[];
  por_dia: ResumenPorDia[];
  top_productos: ResumenTopProducto[];
  por_mesero?: ResumenMesero[];
  por_clase?: ResumenClase[];
  resumen_financiero?: ResumenFinanciero | null;
  comisiones_estimadas?: ComisionesEstimadas | null;
  deltas?: ResumenDeltas | null;
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

export type VentasImportadasPurgeResult = {
  status: string;
  registros_retirados: number;
  ventas_turno_eliminadas: number;
  modo: string;
  sucursal_nombre: string;
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

export async function patchSwissSucursal(sucursal_id: string, body: { sync_password?: string }) {
  const { data } = await api.patch<SwissSucursalBrief>(`/swiss-admin/sucursales/${sucursal_id}`, body);
  return data;
}

export async function deleteSwissSucursal(sucursal_id: string) {
  // POST /delete: mismo efecto que DELETE; evita 405 en proxies o despliegues que no exponen DELETE.
  const { data } = await api.post(`/swiss-admin/sucursales/${sucursal_id}/delete`);
  return data;
}

export async function fetchSwissSucursalLogs(sucursal_id: string, limit = 50) {
  const { data } = await api.get<SwissSucursalLogsItem[]>(`/swiss-admin/sucursales/${sucursal_id}/logs`, {
    params: { limit },
  });
  return data;
}

export async function deleteSwissSucursalVentasImportadas(
  sucursal_id: string,
  body: {
    modo: 'completo' | 'rango';
    fecha_desde?: string;
    fecha_hasta?: string;
  }
) {
  const { data } = await api.delete<VentasImportadasPurgeResult>(
    `/swiss-admin/sucursales/${sucursal_id}/ventas-importadas`,
    {
      params: {
        modo: body.modo,
        ...(body.fecha_desde ? { fecha_desde: body.fecha_desde } : {}),
        ...(body.fecha_hasta ? { fecha_hasta: body.fecha_hasta } : {}),
      },
    }
  );
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

export async function patchSwissDashboardUser(
  user_id: string,
  body: {
    password?: string;
    nombre?: string | null;
    sucursal_ids?: string[];
    catalogo_maestro_id?: string | null;
  }
) {
  const payload: Record<string, unknown> = {};
  if (body.password !== undefined && body.password !== '') payload.password = body.password;
  if (body.nombre !== undefined) payload.nombre = body.nombre;
  if (body.sucursal_ids !== undefined) payload.sucursal_ids = body.sucursal_ids;
  if (body.catalogo_maestro_id !== undefined) payload.catalogo_maestro_id = body.catalogo_maestro_id;
  const { data } = await api.patch<SwissAdminUserBrief>(`/swiss-admin/users/${user_id}`, payload);
  return data;
}

export async function deleteSwissDashboardUser(user_id: string) {
  const { data } = await api.post(`/swiss-admin/users/${user_id}/delete`);
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

export type MetodoPagoAliasBrief = {
  id: string;
  sucursal_id: string;
  alias: string;
  nombre_canonico: string;
};

export async function fetchSwissMetodosPagoAlias(sucursal_id?: string) {
  const { data } = await api.get<MetodoPagoAliasBrief[]>('/swiss-admin/metodos-pago-alias', {
    params: sucursal_id ? { sucursal_id } : {},
  });
  return data;
}

export async function createSwissMetodoPagoAlias(body: {
  sucursal_id: string;
  alias: string;
  nombre_canonico: string;
}) {
  const { data } = await api.post<MetodoPagoAliasBrief>('/swiss-admin/metodos-pago-alias', body);
  return data;
}

export async function patchSwissMetodoPagoAlias(
  rule_id: string,
  body: { alias?: string; nombre_canonico?: string }
) {
  const { data } = await api.patch<MetodoPagoAliasBrief>(`/swiss-admin/metodos-pago-alias/${rule_id}`, body);
  return data;
}

export async function deleteSwissMetodoPagoAlias(rule_id: string) {
  await api.delete(`/swiss-admin/metodos-pago-alias/${rule_id}`);
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
  const { data } = await api.post(`/swiss-admin/config/admin-users/${user_id}/delete`);
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
  sucursalIds?: string[] | undefined,
  opts?: { includePrevious?: boolean }
) {
  const sp = new URLSearchParams();
  sp.set('fecha_desde', fechaDesde);
  sp.set('fecha_hasta', fechaHasta);
  if (opts?.includePrevious) sp.set('include_previous', 'true');
  if (sucursalIds && sucursalIds.length > 0) {
    for (const id of sucursalIds) {
      if (id) sp.append('sucursal_ids', id);
    }
  }
  const { data } = await api.get<Resumen>(`/dashboard/resumen?${sp.toString()}`);
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
  const { data } = await api.get('/dashboard/export/top10', { responseType: 'blob' });
  return data as Blob;
}

export type SwissImportLayoutResult = {
  ok: boolean;
  rules_applied: number;
  errors: string[];
  error?: string | null;
};

export async function downloadSwissCatalogProductTemplate(sucursalIds?: string[]) {
  const sp = new URLSearchParams();
  if (sucursalIds?.length) {
    for (const id of sucursalIds) {
      if (id) sp.append('sucursal_ids', id);
    }
  }
  const q = sp.toString();
  const { data } = await api.get(`/swiss-admin/catalogos/plantilla-productos.xlsx${q ? `?${q}` : ''}`, {
    responseType: 'blob',
  });
  return data as Blob;
}

export async function importSwissCatalogProductLayout(catalogoId: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<SwissImportLayoutResult>(
    `/swiss-admin/catalogos/${catalogoId}/import-productos-layout`,
    form
  );
  return data;
}

export async function downloadSwissMetodosPlantilla() {
  const { data } = await api.get('/swiss-admin/metodos-pago-alias/plantilla.xlsx', { responseType: 'blob' });
  return data as Blob;
}

export async function importSwissMetodosPagoLayout(sucursalId: string, file: File) {
  const form = new FormData();
  form.append('sucursal_id', sucursalId);
  form.append('file', file);
  const { data } = await api.post<SwissImportLayoutResult>('/swiss-admin/metodos-pago-alias/import', form);
  return data;
}
