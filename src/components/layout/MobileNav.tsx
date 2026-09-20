import { useLocation, useNavigate, NavLink } from 'react-router-dom';
import { Home, Refrigerator, ChefHat, ShoppingBag, Plus } from 'lucide-react';
import { clsx } from 'clsx';

const navItems = [
  { path: '/', icon: Home, label: 'Home', isAction: false },
  { path: '/pantry', icon: Refrigerator, label: 'Pantry', isAction: false },
  { path: '/add', icon: Plus, label: 'Add', isAction: true },
  { path: '/rescue', icon: ChefHat, label: 'Rescue', isAction: false },
  { path: '/shopping', icon: ShoppingBag, label: 'Shopping', isAction: false },
];

export function MobileNav() {
  const location = useLocation();
  const navigate = useNavigate();
  
  const activeIndex = navItems.findIndex(item => {
    if (item.isAction) return false;
    if (item.path === '/') return location.pathname === '/';
    return location.pathname.startsWith(item.path);
  });
  
  const safeActiveIndex = activeIndex >= 0 ? activeIndex : 0;

  return (
    <nav className="lg:hidden fixed bottom-6 left-0 right-0 z-40 px-4 pb-safe pointer-events-none">
      <div className="bg-surface/90 backdrop-blur-xl rounded-[2rem] h-[4.5rem] flex relative shadow-[0_10px_40px_var(--neo-shadow)] max-w-sm mx-auto pointer-events-auto border border-neo-border/10">
        
        {/* Animated Indicator Background */}
        <div 
          className="absolute top-0 left-0 h-full w-1/5 pointer-events-none transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] flex items-start justify-center"
          style={{ transform: `translateX(${safeActiveIndex * 100}%)` }}
        >
          {/* Exactly 50x50 circle, centered relative to the slot, pulled up by 20px from top */}
          <div className="w-[50px] h-[50px] mt-[-20px] bg-primary rounded-full shadow-[0_4px_12px_var(--neo-shadow)] border-[4px] border-surface" />
        </div>

        {/* Nav Items */}
        {navItems.map((item, i) => {
          if (item.isAction) {
            return (
              <div key="action" className="flex-1 relative flex justify-center h-full items-center z-20">
                <button 
                  onClick={() => navigate(item.path)}
                  className="absolute -top-7 w-[3.5rem] h-[3.5rem] bg-primary text-white rounded-[1.25rem] flex items-center justify-center shadow-[0_8px_16px_var(--neo-shadow)] border-2 border-neo-border hover:scale-105 active:scale-95 transition-transform rotate-3"
                >
                  <Plus className="w-8 h-8" strokeWidth={3} />
                </button>
              </div>
            );
          }

          const isActive = i === safeActiveIndex;
          return (
            <NavLink 
              key={item.path} 
              to={item.path} 
              className="flex-1 relative z-10 flex items-center justify-center h-full cursor-pointer tap-highlight-transparent"
            >
              {/* Icon Wrapper matches the exact dimensions and offset of the circle */}
              <div 
                className={clsx(
                  "absolute transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] flex items-center justify-center pointer-events-none w-[50px] h-[50px]",
                  isActive ? "top-[-20px] text-white" : "top-[10px] text-muted hover:text-text"
                )}
              >
                <item.icon className="w-[22px] h-[22px]" strokeWidth={isActive ? 2.5 : 2} />
              </div>
              
              <span 
                className={clsx(
                  "absolute bottom-2.5 text-[10px] font-black transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] pointer-events-none uppercase tracking-wider",
                  isActive ? "text-primary opacity-100" : "text-muted opacity-100"
                )}
              >
                {item.label}
              </span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
