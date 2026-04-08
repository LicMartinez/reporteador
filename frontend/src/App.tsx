import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import DashboardLayout from './components/dashboard/DashboardLayout';
import ResumenPage from './pages/dashboard/ResumenPage';
import VentasPage from './pages/dashboard/VentasPage';
import ProductosPage from './pages/dashboard/ProductosPage';
import MeserosPage from './pages/dashboard/MeserosPage';
import PagosPage from './pages/dashboard/PagosPage';
import SwissAdminPortal from './pages/SwissAdminPortal';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 text-slate-600">
        Cargando…
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

/** El dashboard de socios no aplica a portal_admin (solo Swiss Admin). */
function SociosDashboardGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 text-slate-600">
        Cargando…
      </div>
    );
  }
  if (user?.portal_admin) {
    return <Navigate to="/swiss-admin" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/swiss-admin"
        element={
          <PrivateRoute>
            <PortalAdminRoute>
              <SwissAdminPortal />
            </PortalAdminRoute>
          </PrivateRoute>
        }
      />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <SociosDashboardGate>
              <DashboardLayout />
            </SociosDashboardGate>
          </PrivateRoute>
        }
      >
        <Route index element={<ResumenPage />} />
        <Route path="ventas" element={<VentasPage />} />
        <Route path="productos" element={<ProductosPage />} />
        <Route path="meseros" element={<MeserosPage />} />
        <Route path="pagos" element={<PagosPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

function PortalAdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div />;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.portal_admin) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-8">
        <div className="max-w-lg w-full bg-white rounded-2xl shadow-sm border p-7">
          <h2 className="text-xl font-bold text-slate-900 mb-2">Acceso restringido</h2>
          <p className="text-slate-600">Tu cuenta no tiene permisos de Swiss Tools Dashboard Admon.</p>
          <a href="/" className="inline-block mt-5 text-blue-700 font-semibold hover:text-blue-800">
            Volver al dashboard
          </a>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}
