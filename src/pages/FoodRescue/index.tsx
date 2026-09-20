import { useState } from 'react';
import { useRecipes } from '../../hooks/useRecipes';
import { Button } from '../../components/ui/Button';
import { Skeleton } from '../../components/ui/Skeleton';
import { FoodImage } from '../../components/ui/FoodImage';
import { CheckCircle2, AlertTriangle, X } from 'lucide-react';
import type { Recipe } from '../../types/recipe';

export function FoodRescue() {
  const { recipes, loading, error, refresh, cookRecipe } = useRecipes();
  const [cooking, setCooking] = useState<Recipe | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const handleConfirmCook = async () => {
    if (!cooking) return;
    setIsSubmitting(true);
    try {
      await cookRecipe(cooking.id);
      setSuccess(cooking.name);
      setTimeout(() => setSuccess(null), 3000);
      setCooking(null);
    } catch (e) {
      alert("Failed to confirm cooking with backend");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-10 pb-12 w-full">
      <header className="pt-2 md:pt-4 text-center">
        <h1 className="text-4xl md:text-5xl font-black tracking-tight text-text mb-3">FOOD RESCUE</h1>
        <p className="text-gray-500 text-lg md:text-xl font-medium">Save these ingredients before they expire.</p>
      </header>

      {success && (
        <div className="p-4 mb-4 rounded-2xl bg-primary-soft border border-primary-soft text-primary-dark flex items-center shadow-sm animate-in fade-in slide-in-from-top-4 max-w-2xl mx-auto">
          <CheckCircle2 className="w-6 h-6 mr-3 text-primary" />
          <span className="font-black">You cooked {success}! Inventory updated.</span>
        </div>
      )}

      {loading ? (
        <div className="max-w-2xl mx-auto space-y-8">
          <Skeleton className="h-[600px] w-full rounded-[3rem]" />
        </div>
      ) : error ? (
        <div className="neo-card rounded-[1.5rem] p-8 text-center flex flex-col items-center max-w-2xl mx-auto">
          <p className="font-black text-gray-900 mb-4">Unable to load recommendations.</p>
          <Button variant="outline" onClick={refresh}>Retry</Button>
        </div>
      ) : recipes.length === 0 ? (
        <div className="text-center py-20 text-gray-500 neo-card rounded-[3rem] font-medium shadow-sm max-w-2xl mx-auto">
          <p className="text-gray-900 font-black text-xl">No food rescue recipes found.</p>
        </div>
      ) : (
        <div className="space-y-12">
          {recipes.map((recipe, idx) => (
            <div key={recipe.id} className="bg-white rounded-[3rem] overflow-hidden shadow-xl border-2 border-neo-border flex flex-col md:flex-row group max-w-5xl mx-auto">
              
              <div className="md:w-1/2 relative h-80 md:h-[600px] overflow-hidden">
                <FoodImage 
                  src={recipe.imageUrl} 
                  alt={recipe.name} 
                  fallbackEmoji={idx % 2 === 0 ? '🍲' : '🥘'}
                  className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-700" 
                />
              </div>

              <div className="md:w-1/2 p-8 md:p-12 flex flex-col bg-white">
                <h3 className="font-black text-gray-900 text-4xl md:text-5xl mb-6 leading-tight">{recipe.name}</h3>
                
                <p className="text-gray-600 text-lg md:text-xl font-medium leading-relaxed mb-8">
                  {recipe.reasoning}
                </p>

                <div className="bg-coral-50/50 border border-coral-50 rounded-[1.5rem] p-6 mb-8">
                  <h4 className="text-xs font-black text-red-500 uppercase tracking-wider mb-4 flex items-center">
                    <AlertTriangle className="w-4 h-4 mr-2" /> Uses ingredients in your pantry
                  </h4>
                  <ul className="space-y-3">
                    {recipe.ingredients?.map(ing => (
                      <li key={ing.name} className="flex items-center justify-between font-black">
                        <span className="text-gray-900">{ing.name}</span>
                        <span className="text-gray-500">{ing.quantity}{ing.unit}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                
                <div className="mt-auto pt-4">
                  <Button 
                    className="w-full rounded-[1.5rem] py-7 text-lg font-black shadow-2xl shadow-primary-soft bg-primary hover:bg-primary-dark" 
                    onClick={() => setCooking(recipe)}
                  >
                    Cook This →
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* COOK CONFIRMATION MODAL */}
      {cooking && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-md animate-in fade-in duration-200">
          <div className="bg-white rounded-[3rem] w-full max-w-md overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="p-8 md:p-10">
              <div className="flex justify-between items-start mb-8">
                <div>
                  <h3 className="text-3xl font-black text-gray-900 mb-2">Did you cook this?</h3>
                  <p className="text-gray-500 font-medium">This will update your pantry inventory.</p>
                </div>
                <button onClick={() => setCooking(null)} className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center text-gray-500 hover:bg-gray-200 transition-colors shrink-0 ml-4">
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-4 mb-10">
                <p className="text-xs font-black text-gray-400 uppercase tracking-wider pl-2">Ingredients consumed</p>
                {cooking.ingredients?.map((ing, i) => (
                  <div key={i} className="flex justify-between items-center bg-gray-50 p-4 rounded-2xl border-2 border-neo-border">
                    <span className="font-black text-gray-900 text-lg">{ing.name}</span>
                    <span className="font-black text-red-500 text-lg">-{ing.quantity}{ing.unit}</span>
                  </div>
                ))}
              </div>

              <div className="flex flex-col gap-4">
                <Button className="w-full rounded-[1.5rem] py-7 text-lg font-black shadow-[6px_6px_0_var(--neo-shadow)] bg-primary hover:bg-primary-dark" onClick={handleConfirmCook} disabled={isSubmitting}>
                  {isSubmitting ? 'Confirming...' : 'Confirm'}
                </Button>
                <button className="w-full py-4 text-gray-500 font-black hover:text-gray-900 transition-colors" onClick={() => setCooking(null)}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
