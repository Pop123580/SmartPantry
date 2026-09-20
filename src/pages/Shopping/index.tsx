import { useState } from 'react';
import { useShopping } from '../../hooks/useShopping';
import { Button } from '../../components/ui/Button';
import { Skeleton } from '../../components/ui/Skeleton';
import { FoodImage } from '../../components/ui/FoodImage';
import { ShoppingBag, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';

export function Shopping() {
  const { items, loading, error, refresh, checkout } = useShopping();
  const [checkingOut, setCheckingOut] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleCheckout = async () => {
    setCheckingOut(true);
    try {
      await checkout();
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (e) {
      alert("Failed to checkout with backend");
    } finally {
      setCheckingOut(false);
    }
  };
  
  const toBuy = items.filter(i => !i.inInventory);
  const doNotBuy = items.filter(i => i.inInventory);

  return (
    <div className="max-w-6xl mx-auto space-y-10 pb-12 w-full">
      <header className="pt-2 md:pt-4">
        <h1 className="text-3xl md:text-5xl font-black tracking-tight text-text mb-3">SMART SHOPPING</h1>
        <p className="text-gray-600 text-lg md:text-xl font-medium max-w-2xl">"Only buy what your household is likely to need."</p>
      </header>

      {success && (
        <div className="p-4 mb-4 rounded-[1.5rem] bg-primary-soft border border-primary-soft text-primary-dark flex items-center shadow-sm">
          <CheckCircle2 className="w-6 h-6 mr-3 text-primary" />
          <span className="font-black">Shopping list confirmed with backend!</span>
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-4">
          <Skeleton className="h-[300px] w-full rounded-[1.5rem]" />
          <Skeleton className="h-[300px] w-full rounded-[1.5rem]" />
          <Skeleton className="h-[300px] w-full rounded-[1.5rem]" />
          <Skeleton className="h-[300px] w-full rounded-[1.5rem]" />
        </div>
      ) : error ? (
        <div className="neo-card rounded-[1.5rem] p-8 text-center flex flex-col items-center">
          <p className="font-black mb-4">Unable to load shopping predictions.</p>
          <Button variant="outline" onClick={refresh}>Retry</Button>
        </div>
      ) : (
        <>
          <section>
            {toBuy.length === 0 ? (
              <div className="text-center py-20 text-gray-500 neo-card rounded-[1.5rem] font-medium shadow-sm">
                <div className="w-24 h-24 bg-sage-100 text-sage-500 rounded-full flex items-center justify-center mx-auto mb-6 text-4xl">🛒</div>
                <p className="text-gray-900 font-black text-2xl mb-2">You're all set.</p>
                <p>Your backend says you don't need to buy anything right now.</p>
              </div>
            ) : (
              <div className="space-y-10">
                
                {/* Horizontal carousel on mobile, grid on larger screens */}
                <div className="w-full overflow-hidden">
                  <div className="flex overflow-x-auto gap-4 md:grid md:grid-cols-2 lg:grid-cols-4 pb-4 scrollbar-hide snap-x">
                    {toBuy.slice(0, 4).map((item) => (
                      <div key={item.id} className="min-w-[240px] md:min-w-0 bg-white rounded-[1.5rem] overflow-hidden shadow-sm border-2 border-neo-border flex flex-col group hover:shadow-xl transition-all shrink-0 snap-start">
                        <div className="h-48 relative p-6 bg-sage-50 flex items-center justify-center">
                          <FoodImage 
                            src={item.imageUrl} 
                            alt={item.name}
                            fallbackEmoji="🛒"
                            className="w-32 h-32 rounded-full shadow-lg object-cover border-4 border-white transform group-hover:scale-110 transition-transform duration-500"
                          />
                        </div>
                        <div className="p-6 text-center flex-1 flex flex-col">
                          <h3 className="font-black text-gray-900 text-2xl mb-2">{item.name}</h3>
                          <p className="text-sm font-black text-amber-600 mb-6">{item.reason}</p>
                          <div className="mt-auto">
                             <button className="w-full py-3 px-4 bg-gray-50 hover:bg-gray-100 rounded-xl font-black text-gray-900 transition-colors flex items-center justify-center gap-2">
                               <span className="text-gray-400">{item.quantity} {item.unit}</span>
                               <span className="w-1.5 h-1.5 rounded-full bg-gray-300"></span>
                               Add to List
                             </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="pt-4 max-w-md mx-auto">
                  <Button 
                    className="w-full rounded-[1.5rem] py-7 text-lg font-black shadow-2xl shadow-gray-200/50 bg-text hover:bg-text flex items-center justify-center gap-2" 
                    onClick={handleCheckout}
                    disabled={checkingOut}
                  >
                    {checkingOut ? 'Processing...' : 'Review & Shop at Amazon Fresh'}
                    {!checkingOut && <ArrowRight className="w-5 h-5" />}
                  </Button>
                </div>
              </div>
            )}
          </section>

          {doNotBuy.length > 0 && (
            <section className="pt-8">
              <h2 className="text-xs font-black text-gray-400 uppercase tracking-wider mb-6 px-2">YOU DON'T NEED</h2>
              <div className="grid gap-4 md:grid-cols-3">
                {doNotBuy.map(item => (
                  <div key={item.id} className="flex items-center p-4 rounded-[1.5rem] bg-white/50 border border-coral-50 backdrop-blur-sm transition-all shadow-sm opacity-80 group hover:opacity-100">
                    <div className="w-14 h-14 bg-red-50 rounded-2xl flex items-center justify-center shrink-0 mr-4">
                      <AlertTriangle className="w-6 h-6 text-red-500" />
                    </div>
                    <div>
                      <span className="font-black text-gray-900 line-through text-lg block">{item.name}</span>
                      <p className="text-xs font-black text-red-500 mt-0.5">{item.quantity}{item.unit} already available.</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
