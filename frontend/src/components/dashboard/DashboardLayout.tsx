import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { DashboardShellProvider, useDashboardShell } from '../../context/DashboardShellContext';
import { changePassword, exportTop10Csv } from '../../api/client';
import { DashboardSidebar } from './DashboardSidebar';
import { DashboardTopbar } from './DashboardTopbar';
import { Menu } from 'lucide-react';

function DashboardLayoutInner() {
  const { err } = useDashboardShell();
  const [pwOpen, setPwOpen] = useState(false);
  const [pwOld, setPwOld] = useState('');
  const [pwNew, setPwNew] = useState('');
  const [pwErr, setPwErr] = useState<string | null>(null);
  const [exportErr, setExportErr] = useState<string | null>(null);
  const [mobileNav, setMobileNav] = useState(false);

  return (
    <div className="min-h-screen bg-slate-100 font-sans text-slate-900">
      <div className="md:hidden flex items-center justify-between px-4 py-3 bg-[#0f172a] text-white">
        <span className="font-bold">SwissTools Pos</span>
        <button
          type="button"
          aria-label="Menú"
          className="p-2 rounded-lg bg-slate-800"
          onClick={() => setMobileNav((v) => !v)}
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>
      {mobileNav && (
        <div className="md:hidden fixed inset-0 z-40 bg-black/50" onClick={() => setMobileNav(false)} />
      )}
      <div className="flex min-h-[calc(100vh-52px)] md:min-h-screen">
        <div
          className={`${
            mobileNav ? 'translate-x-0' : '-translate-x-full'
          } md:translate-x-0 fixed md:static inset-y-0 left-0 z-50 md:z-auto transition-transform md:inset-auto`}
        >
          <DashboardSidebar
            onChangePassword={() => {
              setPwOpen(true);
              setPwErr(null);
              setMobileNav(false);
            }}
            onExportTop10={async () => {
              setExportErr(null);
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
                setMobileNav(false);
              } catch {
                setExportErr('No se pudo exportar Top 10.');
              }
            }}
            onExportExcel={() => {}}
            onExportPdf={() => {}}
          />
        </div>
        <div className="flex-1 flex flex-col min-w-0">
          <DashboardTopbar />
          <main className="flex-1 p-6 md:p-8 overflow-auto">
            {exportErr && <p className="mb-4 text-sm text-red-600">{exportErr}</p>}
            {err && <p className="mb-4 text-sm text-red-600">{err}</p>}
            <Outlet />
          </main>
        </div>
      </div>

      {pwOpen && <PasswordModal onClose={() => setPwOpen(false)} pwOld={pwOld} setPwOld={setPwOld} pwNew={pwNew} setPwNew={setPwNew} pwErr={pwErr} setPwErr={setPwErr} />}
    </div>
  );
}

function PasswordModal({
  onClose,
  pwOld,
  setPwOld,
  pwNew,
  setPwNew,
  pwErr,
  setPwErr,
}: {
  onClose: () => void;
  pwOld: string;
  setPwOld: (s: string) => void;
  pwNew: string;
  setPwNew: (s: string) => void;
  pwErr: string | null;
  setPwErr: (s: string | null) => void;
}) {
  return (
    <div className="fixed inset-0 z-[60] bg-black/40 flex items-center justify-center p-4">
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
              className="w-full rounded-xl border border-slate-200 px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nueva contraseña</label>
            <input
              type="password"
              value={pwNew}
              onChange={(e) => setPwNew(e.target.value)}
              className="w-full rounded-xl border border-slate-200 px-4 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div className="mt-5 flex gap-3">
          <button
            type="button"
            className="flex-1 py-3 rounded-xl bg-slate-100 text-slate-800 font-semibold hover:bg-slate-200"
            onClick={onClose}
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
                onClose();
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
  );
}

export default function DashboardLayout() {
  return (
    <DashboardShellProvider>
      <DashboardLayoutInner />
    </DashboardShellProvider>
  );
}
