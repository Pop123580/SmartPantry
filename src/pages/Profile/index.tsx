import { useTheme, ThemeColor } from '../../hooks/useTheme';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../../components/ui/Button';
import { Check, LogOut, Users, Bell, ShoppingBag, ChefHat, ChevronRight } from 'lucide-react';
import { clsx } from 'clsx';
import { useNavigate } from 'react-router-dom';

export function Profile() {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const colors: { id: ThemeColor, hex: string, name: string }[] = [
    { id: 'green', hex: '#10b981', name: 'Green' },
    { id: 'yellow', hex: '#eab308', name: 'Yellow' },
    { id: 'blue', hex: '#3b82f6', name: 'Blue' },
    { id: 'purple', hex: '#8b5cf6', name: 'Purple' },
    { id: 'pink', hex: '#ec4899', name: 'Pink' },
    { id: 'orange', hex: '#f97316', name: 'Orange' },
    { id: 'red', hex: '#ef4444', name: 'Red' },
  ];

  return (
    <div className="space-y-8 pb-10 max-w-3xl mx-auto w-full">
      <header className="pt-2 md:pt-4 border-b-2 border-neo-border pb-4">
        <h1 className="text-3xl md:text-4xl font-black tracking-tight text-text uppercase">Settings</h1>
        <p className="text-muted mt-1.5 text-base font-bold">Manage your SmartPantry experience.</p>
      </header>

      <section>
        <h2 className="text-xs font-black text-text uppercase tracking-wider mb-4 flex items-center">
          Appearance
          <div className="h-[2px] bg-neo-border flex-1 ml-4 opacity-20"></div>
        </h2>
        
        <div className="neo-card overflow-hidden">
          <div className="p-4 md:p-6 pb-0 md:pb-0">
            <h3 className="font-bold text-lg mb-0.5 text-text">Theme Color</h3>
            <p className="text-muted text-xs md:text-sm font-bold mb-4">Choose your SmartPantry color.</p>
          </div>
          
          <div className="px-4 md:px-6 pb-4 md:pb-6 overflow-x-auto scrollbar-hide">
            <div className="flex gap-4 min-w-max">
              {colors.map(c => (
                <button 
                  key={c.id} 
                  onClick={() => setTheme(c.id)}
                  className="flex flex-col items-center gap-2 group transition-all shrink-0 w-12"
                >
                  <div 
                    className={clsx(
                      "w-[46px] h-[54px] rounded-[1.25rem] flex items-center justify-center transition-transform",
                      theme === c.id ? "scale-105 border-2 border-neo-border shadow-[2px_2px_0_var(--neo-shadow)]" : "hover:scale-105 border-2 border-transparent"
                    )}
                    style={{ backgroundColor: c.hex }}
                  >
                    {theme === c.id && <Check className="w-5 h-5 text-white" strokeWidth={3} />}
                  </div>
                  <span className={clsx("text-[9px] font-black transition-colors uppercase tracking-wider", theme === c.id ? "text-text" : "text-muted")}>
                    {c.name}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-xs font-black text-text uppercase tracking-wider mb-4 flex items-center">
          Household
          <div className="h-[2px] bg-neo-border flex-1 ml-4 opacity-20"></div>
        </h2>
        
        <div className="neo-card overflow-hidden divide-y-2 divide-neo-border">
           <button className="w-full p-4 md:p-6 flex items-center justify-between hover:bg-gray-50 transition-colors text-left group">
              <div className="flex items-center gap-4">
                 <div className="w-12 h-12 rounded-full bg-primary-soft text-primary flex items-center justify-center text-lg font-black border-2 border-primary/30 group-hover:scale-105 transition-transform">
                    {user?.name?.charAt(0) || 'U'}
                 </div>
                 <div>
                   <h3 className="font-black text-lg text-text">{user?.name || 'User'}</h3>
                   <p className="text-muted text-xs font-bold">Household Admin</p>
                 </div>
              </div>
              <ChevronRight className="w-5 h-5 text-muted group-hover:text-text transition-colors" />
           </button>
           
           <button className="w-full p-4 md:p-6 flex items-center justify-between hover:bg-gray-50 transition-colors text-left group">
              <div className="flex items-center gap-4">
                 <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-text border-2 border-transparent group-hover:border-neo-border transition-colors">
                    <Users className="w-5 h-5" />
                 </div>
                 <div>
                   <h3 className="font-bold text-base text-text">Household Members</h3>
                   <p className="text-muted text-xs font-bold">Manage your family</p>
                 </div>
              </div>
              <ChevronRight className="w-5 h-5 text-muted group-hover:text-text transition-colors" />
           </button>
        </div>
      </section>

      <section>
        <h2 className="text-xs font-black text-text uppercase tracking-wider mb-4 flex items-center">
          Preferences
          <div className="h-[2px] bg-neo-border flex-1 ml-4 opacity-20"></div>
        </h2>
        
        <div className="neo-card overflow-hidden divide-y-2 divide-neo-border">
           
           <div className="w-full p-4 md:p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                 <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-text">
                    <Bell className="w-5 h-5" />
                 </div>
                 <span className="font-bold text-base text-text">Expiry Alerts</span>
              </div>
              <div className="w-10 h-6 bg-primary rounded-full relative shadow-inner cursor-pointer border-2 border-neo-border">
                 <div className="absolute right-1 top-0.5 w-4 h-4 bg-white rounded-full border border-neo-border/20"></div>
              </div>
           </div>

           <div className="w-full p-4 md:p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                 <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-text">
                    <ShoppingBag className="w-5 h-5" />
                 </div>
                 <span className="font-bold text-base text-text">Shopping Predictions</span>
              </div>
              <div className="w-10 h-6 bg-primary rounded-full relative shadow-inner cursor-pointer border-2 border-neo-border">
                 <div className="absolute right-1 top-0.5 w-4 h-4 bg-white rounded-full border border-neo-border/20"></div>
              </div>
           </div>

           <div className="w-full p-4 md:p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                 <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-text">
                    <ChefHat className="w-5 h-5" />
                 </div>
                 <span className="font-bold text-base text-text">Recipe Suggestions</span>
              </div>
              <div className="w-10 h-6 bg-primary rounded-full relative shadow-inner cursor-pointer border-2 border-neo-border">
                 <div className="absolute right-1 top-0.5 w-4 h-4 bg-white rounded-full border border-neo-border/20"></div>
              </div>
           </div>

        </div>
      </section>
      
      <section className="pt-2">
         <button
           className="w-full neo-card p-5 flex items-center justify-center gap-2 text-red-500 font-bold hover:bg-red-50 transition-colors"
           onClick={async () => { await logout(); navigate('/login'); }}
         >
            <LogOut className="w-5 h-5" />
            <span className="text-lg">Sign Out</span>
         </button>
      </section>
    </div>
  );
}
