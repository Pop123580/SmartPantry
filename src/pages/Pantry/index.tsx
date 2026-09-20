import { useState } from 'react';
import { usePantry } from '../../hooks/usePantry';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { FoodImage } from '../../components/ui/FoodImage';
import { Search, SlidersHorizontal, AlertTriangle } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { clsx } from 'clsx';

export function Pantry() {
  const { items, loading, error, refresh } = usePantry();
  const [filter, setFilter] = useState('All');
  const [search, setSearch] = useState('');

  const filteredItems = items.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(search.toLowerCase());
    if (!matchesSearch) return false;
    
    if (filter === 'Expiring') return item.status === 'expiring_soon';
    if (filter === 'High Risk') return item.risk === 'high';
    if (filter === 'Running Low') return item.status === 'running_low';
    if (filter === 'Safe') return item.status === 'safe';
    return true;
  });

  const filterOptions = ['All', 'Expiring', 'High Risk', 'Running Low', 'Safe'];

  return (
    <div className="space-y-6 md:space-y-8 pb-10 w-full overflow-hidden">
      <header className="pt-2 md:pt-4">
        <h1 className="text-3xl md:text-4xl font-black tracking-tight text-text">Your Pantry</h1>
        <p className="text-muted mt-2 text-lg">Manage your household inventory.</p>
      </header>
      
      <div className="flex items-center gap-3 w-full">
        <div className="relative flex-1 min-w-0">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 focus-within:text-primary" />
          <input 
            type="text" 
            placeholder="Search groceries..." 
            className="w-full pl-12 pr-4 py-4 neo-card rounded-[1.5rem] focus:outline-none focus:ring-2 focus:ring-primary font-medium"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button className="w-14 h-14 neo-card rounded-[1.5rem] flex items-center justify-center shrink-0 text-gray-600 hover:text-text transition-colors">
          <SlidersHorizontal className="w-6 h-6" />
        </button>
      </div>

      <div className="w-full -mx-4 px-4 sm:mx-0 sm:px-0">
        <div className="flex gap-3 overflow-x-auto pb-4 scrollbar-hide pr-4 min-w-full">
          {filterOptions.map(f => (
            <button 
              key={f}
              onClick={() => setFilter(f)}
              className={clsx(
                "whitespace-nowrap px-6 py-2.5 rounded-full text-sm font-black transition-all shadow-sm border shrink-0",
                filter === f 
                  ? 'bg-text text-white border-text shadow-md' 
                  : 'bg-white/80 backdrop-blur-sm text-muted border-white hover:bg-white'
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <Skeleton className="h-64 w-full rounded-[1.5rem]" />
          <Skeleton className="h-64 w-full rounded-[1.5rem]" />
          <Skeleton className="h-64 w-full rounded-[1.5rem]" />
          <Skeleton className="h-64 w-full rounded-[1.5rem]" />
        </div>
      ) : error ? (
        <div className="neo-card rounded-[1.5rem] p-8 text-center flex flex-col items-center">
          <p className="font-black text-text mb-4">Failed to load pantry data.</p>
          <Button variant="outline" onClick={refresh}>Retry</Button>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-20 text-muted neo-card rounded-[1.5rem] font-medium shadow-sm">
          <div className="w-20 h-20 bg-primary-soft rounded-full flex items-center justify-center mx-auto mb-4 text-4xl">
            🥬
          </div>
          <p className="text-text font-black text-xl">No groceries found.</p>
          <p className="text-muted mt-2">Try scanning a receipt to add items.</p>
        </div>
      ) : (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredItems.map(item => (
            <div key={item.id} className="bg-white rounded-[1.5rem] overflow-hidden shadow-sm border-2 border-neo-border hover:shadow-lg transition-all flex flex-col group min-w-0">
              <div className="h-40 relative shrink-0">
                <FoodImage 
                  src={item.imageUrl} 
                  alt={item.name} 
                  fallbackEmoji={item.category === 'Vegetable' ? '🥬' : item.category === 'Dairy' ? '🥛' : '🛒'}
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-3 right-3">
                  <Badge variant={
                    item.risk === 'high' ? 'destructive' :
                    item.status === 'running_low' ? 'warning' :
                    item.status === 'expiring_soon' ? 'warning' : 'success'
                  } className="rounded-xl px-3 py-1 text-[10px] font-black uppercase tracking-wider shadow-sm backdrop-blur-md bg-white/90">
                    {item.status.replace('_', ' ')}
                  </Badge>
                </div>
              </div>
              
              <div className="p-5 flex flex-col flex-1 min-w-0">
                <h3 className="font-black text-text text-xl truncate mb-1">{item.name}</h3>
                <p className="text-sm text-muted font-medium mb-4">{item.category}</p>

                {item.risk === 'high' && (
                  <p className="text-xs font-black text-red-500 mb-3 flex items-center">
                     <AlertTriangle className="w-3.5 h-3.5 mr-1 shrink-0" /> HIGH WASTE RISK
                  </p>
                )}

                <div className="flex items-center justify-between mt-auto">
                  <span className="bg-primary-soft text-primary-dark px-3 py-1.5 rounded-xl text-sm font-black border border-primary-soft">
                    {item.quantity}{item.unit}
                  </span>
                  <button className="text-sm font-black text-primary px-3 py-1.5 rounded-xl hover:bg-primary-soft transition-colors">
                    Edit
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
