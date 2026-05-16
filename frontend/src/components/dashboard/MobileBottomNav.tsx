import { NavLink } from 'react-router-dom';
import { BarChart3, CreditCard, LayoutDashboard, Package, UserCircle } from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Resumen' },
  { to: '/ventas', icon: BarChart3, label: 'Ventas' },
  { to: '/productos', icon: Package, label: 'Productos' },
  { to: '/meseros', icon: UserCircle, label: 'Meseros' },
  { to: '/pagos', icon: CreditCard, label: 'Pagos' },
];

export function MobileBottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-slate-200 safe-area-bottom">
      <div className="flex items-stretch justify-around h-16">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center flex-1 gap-0.5 text-[10px] font-semibold transition-colors ${
                isActive
                  ? 'text-blue-600'
                  : 'text-slate-400 active:text-slate-600'
              }`
            }
          >
            <Icon className="w-5 h-5" />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
