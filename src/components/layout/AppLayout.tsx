import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { Home, Refrigerator, ChefHat, ShoppingBag, Plus, User } from 'lucide-react';
import { clsx } from 'clsx';
import { MobileNav } from './MobileNav';
import { useTheme } from '../../hooks/useTheme';

export function AppLayout() {
  const navigate = useNavigate();
  useTheme(); // Initialize theme

  const navItems = [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/pantry', icon: Refrigerator, label: 'Pantry' },
    { to: '/rescue', icon: ChefHat, label: 'Rescue' },
    { to: '/shopping', icon: ShoppingBag, label: 'Shopping' },
    { to: '/profile', icon: User, label: 'Profile' },
  ];

  return (
    <div className="min-h-screen flex flex-col lg:flex-row w-full max-w-[100vw] overflow-x-hidden">
      {/* Desktop Sidebar (lg and up) */}
      <aside className="hidden lg:flex flex-col w-72 glass-panel border-r sticky top-0 h-screen p-8 z-50 shrink-0">
        <div className="flex items-center gap-4 mb-12">
          <div className="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center border-2 border-neo-border shadow-[3px_3px_0_var(--neo-shadow)]">
            <Refrigerator className="text-white w-8 h-8" />
          </div>
          <span className="text-3xl font-black tracking-tight text-text">SmartPantry</span>
        </div>
        
        <nav className="flex-1 space-y-4">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-5 px-6 py-4 rounded-2xl transition-all duration-300 font-bold text-xl',
                  isActive 
                    ? 'bg-primary-soft text-primary border-2 border-primary/20 shadow-sm' 
                    : 'text-muted hover:bg-white/50 hover:text-text border-2 border-transparent'
                )
              }
            >
              <item.icon className={clsx("w-7 h-7", "transition-colors")} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto">
          <button 
            className="neo-button w-full py-5 text-xl flex items-center justify-center gap-3" 
            onClick={() => navigate('/add')}
          >
            <Plus className="w-7 h-7" />
            Add Grocery
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 w-full lg:w-auto min-w-0 pb-48 lg:pb-12">
        <div className="w-full max-w-5xl mx-auto p-4 md:p-8 lg:p-12 overflow-x-hidden">
          <Outlet />
        </div>
      </main>

      {/* Mobile/Tablet Navigation */}
      <MobileNav />
    </div>
  );
}
