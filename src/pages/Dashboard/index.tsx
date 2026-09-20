import { usePantry } from '../../hooks/usePantry';
import { useRecipes } from '../../hooks/useRecipes';
import { Button } from '../../components/ui/Button';
import { Skeleton } from '../../components/ui/Skeleton';
import { FoodImage } from '../../components/ui/FoodImage';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { AlertTriangle, ChefHat, Search, Bell, Leaf } from 'lucide-react';
import { BotanicalMandalaPattern } from '../../components/ui/BotanicalMandalaPattern';

export function Dashboard() {
  const { user } = useAuth();
  const { items: pantryItems, loading: pantryLoading, error: pantryError, refresh: refreshPantry } = usePantry();
  const { recipes } = useRecipes();
  const navigate = useNavigate();

  const hour = new Date().getHours();
  let timeGreeting = 'Good evening';
  if (hour < 12) timeGreeting = 'Good morning';
  else if (hour < 18) timeGreeting = 'Good afternoon';

  const firstName = user?.name || 'there';

  const highRisk = pantryItems.filter(i => i.risk === 'high');
  const expiringSoon = pantryItems.filter(i => i.status === 'expiring_soon');
  const safe = pantryItems.filter(i => i.status === 'safe');

  const needsAttention = [...highRisk, ...expiringSoon].slice(0, 1);

  return (
    <div className="space-y-10 pb-10">
      
      {/* REDESIGNED HEADER WITH MANDALA PATTERN */}
      <header className="pt-4 md:pt-6 mb-8 relative">
        <BotanicalMandalaPattern />
        
        <div className="relative z-10">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6 mb-8">
            <div className="flex justify-between items-start w-full md:w-auto">
              <div>
                <h1 className="text-3xl md:text-4xl font-black tracking-tight text-text flex items-center drop-shadow-sm">
                  {timeGreeting}, {firstName} <span className="ml-2 text-3xl">👋</span>
                </h1>
                <p className="text-text/80 mt-2 text-[15px] md:text-lg font-bold drop-shadow-sm">Here's what's happening in your kitchen today.</p>
              </div>
              
              <div className="flex items-center gap-3 md:hidden shrink-0 ml-4">
                <button aria-label="Notifications" className="w-11 h-11 rounded-[1.25rem] bg-surface/80 backdrop-blur-md flex items-center justify-center text-text shadow-sm border border-neo-border/20">
                  <Bell className="w-5 h-5" />
                </button>
                <button aria-label="Profile" onClick={() => navigate('/profile')} className="w-11 h-11 rounded-[1.25rem] bg-primary text-white flex items-center justify-center font-bold text-lg shadow-[2px_2px_0_var(--neo-shadow)] border-2 border-neo-border">
                  {firstName.charAt(0).toUpperCase()}
                </button>
              </div>
            </div>
            
            <div className="hidden md:flex items-center gap-4 shrink-0">
               <button aria-label="Notifications" className="w-14 h-14 rounded-[1.25rem] bg-surface/80 backdrop-blur-md flex items-center justify-center text-text shadow-sm border border-neo-border/20 hover:scale-105 transition-transform">
                 <Bell className="w-6 h-6" />
               </button>
               <button aria-label="Profile" onClick={() => navigate('/profile')} className="w-14 h-14 rounded-[1.25rem] bg-primary text-white flex items-center justify-center font-bold text-2xl shadow-[3px_3px_0_var(--neo-shadow)] border-2 border-neo-border hover:scale-105 transition-transform">
                 {firstName.charAt(0).toUpperCase()}
               </button>
            </div>
          </div>
          
          <div className="relative group">
            <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-muted group-focus-within:text-primary transition-colors z-10" />
            <input 
              type="text" 
              placeholder="Search your pantry..." 
              className="w-full pl-14 pr-6 py-5 bg-surface/90 backdrop-blur-xl border-2 border-neo-border shadow-[4px_4px_0_var(--neo-shadow)] rounded-[1.5rem] focus:outline-none focus:ring-4 focus:ring-primary-soft font-bold text-lg transition-all text-text placeholder:text-muted relative z-20" 
            />
          </div>
        </div>
      </header>

      {/* PANTRY SUMMARY */}
      <section className="relative z-10">
        {pantryLoading ? (
          <Skeleton className="h-40 w-full rounded-[2rem]" />
        ) : pantryError ? (
          <div className="neo-card p-6 flex flex-col items-center justify-center text-center bg-white">
             <AlertTriangle className="w-8 h-8 text-amber-500 mb-2" />
             <p className="font-bold text-text mb-1">Pantry data unavailable</p>
             <p className="text-sm text-muted mb-4">Couldn't load your pantry right now.</p>
             <Button variant="outline" size="sm" onClick={refreshPantry}>Retry</Button>
          </div>
        ) : (
          <div className="neo-card p-6 md:p-8 overflow-hidden relative bg-white">
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary-soft rounded-full blur-3xl opacity-50 -mr-16 -mt-16 pointer-events-none"></div>
            
            <div className="flex items-center justify-between mb-8 relative z-10">
              <h2 className="text-sm font-black text-text uppercase tracking-wider">YOUR PANTRY</h2>
              <button onClick={() => navigate('/pantry')} className="text-sm font-bold text-primary bg-primary-soft px-4 py-2 rounded-xl hover:bg-primary hover:text-white transition-colors border-2 border-transparent hover:border-neo-border">
                View All
              </button>
            </div>
            
            <div className="grid grid-cols-3 divide-x-2 divide-neo-border/10 relative z-10">
              <div className="text-center px-2">
                <div className="text-4xl md:text-5xl font-black text-text mb-2">{safe.length}</div>
                <div className="text-[10px] md:text-sm font-bold text-muted uppercase tracking-wider">Safe</div>
              </div>
              <div className="text-center px-2">
                <div className="text-4xl md:text-5xl font-black text-amber-500 mb-2">{expiringSoon.length}</div>
                <div className="text-[10px] md:text-sm font-bold text-amber-600 uppercase tracking-wider">Expiring</div>
              </div>
              <div className="text-center px-2">
                <div className="text-4xl md:text-5xl font-black text-red-500 mb-2">{highRisk.length}</div>
                <div className="text-[10px] md:text-sm font-bold text-red-500 uppercase tracking-wider">High Risk</div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* NEEDS ATTENTION FEATURE */}
      <section className="relative z-10">
        <h2 className="text-sm font-black text-text uppercase tracking-wider mb-6 px-2">NEEDS ATTENTION</h2>
        {pantryLoading ? (
          <Skeleton className="h-[400px] w-full rounded-[2rem]" />
        ) : !pantryError && needsAttention.length > 0 ? (
          <div className="neo-card overflow-hidden flex flex-col md:flex-row group cursor-pointer hover:shadow-[6px_6px_0_var(--neo-shadow)] transition-all bg-white" onClick={() => navigate('/rescue')}>
            <div className="h-64 md:h-auto md:w-2/5 relative shrink-0 border-b-2 md:border-b-0 md:border-r-2 border-neo-border bg-white">
              <FoodImage 
                src={needsAttention[0].imageUrl}
                alt={needsAttention[0].name}
                fallbackEmoji="🥬"
                className="absolute inset-0 w-full h-full transform group-hover:scale-105 transition-transform duration-700"
              />
              <div className="absolute top-4 left-4">
                <div className="bg-white/90 backdrop-blur-md text-red-600 text-xs font-bold px-3 py-1.5 rounded-full flex items-center shadow-sm uppercase tracking-wider border-2 border-red-200">
                  <AlertTriangle className="w-3.5 h-3.5 mr-1.5" /> High Waste Risk
                </div>
              </div>
            </div>
            <div className="p-6 md:p-8 flex flex-col justify-center flex-1 bg-white">
              <div className="mb-2">
                <span className="text-sm font-bold text-amber-600 uppercase tracking-wider">Expires soon</span>
              </div>
              <h3 className="text-3xl font-black text-text mb-2">{needsAttention[0].name}</h3>
              <p className="text-muted font-bold text-lg mb-8">{needsAttention[0].quantity}{needsAttention[0].unit} remaining in your pantry.</p>
              
              <button className="neo-button w-full md:w-auto py-4 px-8 text-lg flex items-center justify-center">
                Use Now →
              </button>
            </div>
          </div>
        ) : !pantryError && (
          <div className="neo-card p-8 text-center bg-white">
            <div className="w-16 h-16 bg-primary-soft text-primary rounded-full flex items-center justify-center mx-auto mb-4 border-2 border-primary/20">
              <Leaf className="w-8 h-8" />
            </div>
            <p className="font-bold text-text text-xl">Looking good!</p>
            <p className="text-muted font-medium mt-2">No items are at risk of wasting right now.</p>
          </div>
        )}
      </section>
      
      {/* FOOD RESCUE QUICK RECOMMENDATION */}
      {recipes.length > 0 && (
        <section className="relative z-10">
          <h2 className="text-sm font-black text-text uppercase tracking-wider mb-6 px-2 flex items-center">
             <ChefHat className="w-5 h-5 mr-2 text-primary" /> TODAY'S SUGGESTION
          </h2>
          <div className="neo-card overflow-hidden flex flex-col cursor-pointer group bg-white" onClick={() => navigate('/rescue')}>
            <div className="h-64 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-t from-gray-900/90 to-transparent z-10" />
              <FoodImage 
                src={recipes[0].imageUrl} 
                alt={recipes[0].name} 
                fallbackEmoji="🍲"
                className="w-full h-full transform group-hover:scale-105 transition-transform duration-700"
              />
              <div className="absolute bottom-6 left-6 right-6 z-20">
                <h3 className="font-black text-white text-3xl mb-2">{recipes[0].name}</h3>
                <p className="text-gray-200 text-sm font-bold line-clamp-1">{recipes[0].reasoning}</p>
              </div>
            </div>
          </div>
        </section>
      )}

    </div>
  );
}
