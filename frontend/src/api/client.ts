import axios from 'axios';

const base = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const api = axios.create({
  baseURL: base.replace(/\/$/, ''),
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const t = localStorage.getItem('restbar_token');
  if (t) {
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('restbar_token');
      localStorage.removeItem('restbar_user');
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
  sucursales: { id: string; nombre: string; rol: string | null }[];
};

export type Resumen = {
  total_ingresos: number;
  num_tickets: number;
  ticket_promedio: number;
  total_efectivo: number;
  total_tarjeta: number;
  por_hora: { name: string; ventas: number }[];
  por_metodo: { name: string; amount: number }[];
};

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

export async function fetchResumen(fechaDesde: string, fechaHasta: string, sucursalId?: string) {
  const { data } = await api.get<Resumen>('/dashboard/resumen', {
    params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta, sucursal_id: sucursalId || undefined },
  });
  return data;
}

export async function fetchSucursalesFilter() {
  const { data } = await api.get<{ id: string; nombre: string }[]>('/dashboard/sucursales');
  return data;
}
