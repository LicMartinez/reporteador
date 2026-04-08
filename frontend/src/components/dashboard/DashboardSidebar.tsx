import { NavLink } from 'react-router-dom';
import {
  Activity,
  BarChart3,
  CreditCard,
  FileSpreadsheet,
  FileText,
  LayoutDashboard,
  LogOut,
  Package,
  UserCircle,
  Users,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const navCls = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 px-4 py-3 rounded-xl font-semibold text-left transition-colors ${
    isActive ? 'bg-blue-600 text-white shadow-md shadow-blue-900/20' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
  }`;

export function DashboardSidebar({
  onChangePassword,
  onExportTop10,
  onExportExcel,
  onExportPdf,
}: {
  onChangePassword: () => void;
  onExportTop10: () => void;
  onExportExcel: () => void;
  onExportPdf: () => void;
}) {
  const { user, logout } = useAuth();

  return (
    <aside className="hidden md:flex w-72 shrink-0 flex-col bg-[#0f172a] text-slate-100 min-h-screen sticky top-0 border-r border-slate-800">
      <div className="p-6 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight">SwissTools Pos</h1>
            <p className="text-[10px] uppercase tracking-widest text-slate-500 font-medium">Dashboard</p>
          </div>
        </div>
      </div>

      <div className="p-4 mx-4 mt-4 rounded-xl bg-slate-800/50 border border-slate-700/50">
        <p className="font-semibold text-sm text-white truncate">{user?.nombre || user?.email}</p>
        <p className="text-xs text-slate-400 mt-1">
          {user?.is_admin && !user?.portal_admin ? 'Administrador' : 'Visor'}
        </p>
      </div>

      <nav className="flex flex-col gap-1 p-4 flex-1">
        <NavLink to="/" end className={navCls}>
          <LayoutDashboard className="w-5 h-5 shrink-0" />
          Resumen general
        </NavLink>
        <NavLink to="/ventas" className={navCls}>
          <BarChart3 className="w-5 h-5 shrink-0" />
          Análisis de ventas
        </NavLink>
        <NavLink to="/productos" className={navCls}>
          <Package className="w-5 h-5 shrink-0" />
          Productos y categorías
        </NavLink>
        <NavLink to="/meseros" className={navCls}>
          <UserCircle className="w-5 h-5 shrink-0" />
          Desempeño meseros
        </NavLink>
        <NavLink to="/pagos" className={navCls}>
          <CreditCard className="w-5 h-5 shrink-0" />
          Métodos de pago
        </NavLink>

        {user?.portal_admin && (
          <NavLink
            to="/swiss-admin"
            className="flex items-center gap-3 px-4 py-3 rounded-xl font-semibold text-left text-slate-300 hover:bg-slate-800 hover:text-white border border-dashed border-slate-600 mt-2"
          >
            <Users className="w-5 h-5 shrink-0" />
            Swiss Admin
          </NavLink>
        )}
      </nav>

      <div className="p-4 border-t border-slate-800 space-y-2">
        <p className="text-[10px] uppercase tracking-wider text-slate-500 px-1 mb-1">Exportar</p>
        <button
          type="button"
          onClick={onExportTop10}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium bg-slate-800 text-slate-200 hover:bg-slate-700"
        >
          <FileSpreadsheet className="w-4 h-4 shrink-0 text-emerald-400" />
          Top 10 (CSV)
        </button>
        <button
          type="button"
          disabled
          title="Próximamente: exportación a Excel"
          onClick={onExportExcel}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium bg-slate-800/40 text-slate-500 cursor-not-allowed opacity-70"
        >
          <FileSpreadsheet className="w-4 h-4 shrink-0" />
          Excel
        </button>
        <button
          type="button"
          disabled
          title="Próximamente: exportación a PDF"
          onClick={onExportPdf}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium bg-slate-800/40 text-slate-500 cursor-not-allowed opacity-70"
        >
          <FileText className="w-4 h-4 shrink-0" />
          PDF
        </button>

        <button
          type="button"
          onClick={onChangePassword}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium text-slate-300 hover:bg-slate-800"
        >
          <CreditCard className="w-4 h-4 shrink-0" />
          Cambiar contraseña
        </button>
        <button
          type="button"
          onClick={() => logout()}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 text-sm font-medium"
        >
          <LogOut className="w-4 h-4" />
          Salir
        </button>
      </div>
    </aside>
  );
}
