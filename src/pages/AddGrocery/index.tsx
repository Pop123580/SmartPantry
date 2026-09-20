import { useState, useRef } from 'react';
import { api } from '../../services/api/client';
import { usePantry } from '../../hooks/usePantry';
import { Button } from '../../components/ui/Button';
import { Camera, CheckCircle2, Trash2, Edit3, Plus, ScanLine } from 'lucide-react';
import type { CreatePantryItemDTO } from '../../types/pantry';
import { useNavigate } from 'react-router-dom';

export function AddGrocery() {
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scannedItems, setScannedItems] = useState<CreatePantryItemDTO[] | null>(null);
  const [adding, setAdding] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { addItem } = usePantry();
  const navigate = useNavigate();

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setProcessing(true);
    setError(null);
    try {
      const items = await api.receipt.uploadReceipt(file);
      if (Array.isArray(items)) {
        setScannedItems(items);
      } else {
        setScannedItems([]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to process receipt');
      setScannedItems(null);
    } finally {
      setProcessing(false);
    }
  };

  const updateItem = (index: number, updates: Partial<CreatePantryItemDTO>) => {
    setScannedItems(prev => {
      if (!prev) return prev;
      const next = [...prev];
      next[index] = { ...next[index], ...updates };
      return next;
    });
  };

  const removeItem = (index: number) => {
    setScannedItems(prev => {
      if (!prev) return prev;
      return prev.filter((_, i) => i !== index);
    });
  };

  const handleAddToPantry = async () => {
    if (!scannedItems || scannedItems.length === 0) return;
    setAdding(true);
    try {
      for (const item of scannedItems) {
        await addItem(item);
      }
      navigate('/pantry');
    } catch (err: any) {
      setError('Failed to add some items. Please try again.');
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto pb-10 w-full flex flex-col md:justify-center md:min-h-[80vh]">
      
      {/* Background illustration */}
      <div className="hidden md:block absolute inset-0 pointer-events-none overflow-hidden z-0">
         <div className="absolute top-20 right-20 w-96 h-96 bg-sage-100 rounded-full blur-3xl opacity-50"></div>
         <div className="absolute bottom-20 left-20 w-80 h-80 bg-primary-soft rounded-full blur-3xl opacity-50"></div>
      </div>

      <div className="neo-card rounded-t-[3rem] md:rounded-[3rem] p-6 md:p-10 shadow-2xl relative z-10 w-full mt-auto md:mt-0 min-h-[70vh] md:min-h-0 flex flex-col">
        <div className="w-12 h-1.5 bg-gray-200 rounded-full mx-auto mb-8 md:hidden"></div>
        
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-black tracking-tight text-gray-900">Add to Pantry</h1>
          <p className="text-gray-500 mt-2 font-medium">Keep track of what you bring home.</p>
        </header>

        {error && (
          <div className="p-4 mb-6 bg-red-50 text-red-700 border border-red-100 rounded-2xl flex items-center shadow-sm">
            ⚠️ <span className="ml-2 font-black">{error}</span>
          </div>
        )}

        {!processing && !scannedItems && (
          <div className="grid gap-4 flex-1 content-center">
            <input 
              type="file" 
              accept="image/*" 
              className="hidden" 
              ref={fileInputRef} 
              onChange={handleFileUpload} 
            />
            
            <button 
              onClick={() => fileInputRef.current?.click()}
              className="w-full text-left neo-button transition-all duration-300 rounded-[1.5rem] p-6 flex items-center gap-6 group shadow-[6px_6px_0_var(--neo-shadow)]"
            >
              <div className="w-16 h-16 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                <ScanLine className="w-8 h-8" />
              </div>
              <div>
                <h3 className="font-black text-xl mb-1">Scan Receipt</h3>
                <p className="text-emerald-100 font-medium text-sm">Automatically identify groceries.</p>
              </div>
            </button>

            <button className="w-full text-left bg-white border-2 border-neo-border opacity-60 rounded-[1.5rem] p-6 flex items-center gap-6 cursor-not-allowed">
              <div className="w-16 h-16 bg-gray-50 text-gray-400 rounded-2xl flex items-center justify-center shrink-0">
                <Camera className="w-8 h-8" />
              </div>
              <div>
                <h3 className="font-black text-gray-900 text-xl mb-1">Scan Barcode</h3>
                <p className="text-gray-500 font-medium text-sm">Coming soon</p>
              </div>
            </button>

            <button className="w-full text-left bg-white border-2 border-neo-border opacity-60 rounded-[1.5rem] p-6 flex items-center gap-6 cursor-not-allowed">
              <div className="w-16 h-16 bg-gray-50 text-gray-400 rounded-2xl flex items-center justify-center shrink-0">
                <Plus className="w-8 h-8" />
              </div>
              <div>
                <h3 className="font-black text-gray-900 text-xl mb-1">Add Manually</h3>
                <p className="text-gray-500 font-medium text-sm">Coming soon</p>
              </div>
            </button>
          </div>
        )}

        {processing && (
          <div className="flex flex-col items-center justify-center text-center space-y-8 flex-1 py-12">
            <div className="relative">
              <div className="absolute inset-0 bg-primary-soft rounded-full animate-ping opacity-75"></div>
              <div className="relative bg-primary-soft w-24 h-24 rounded-full flex items-center justify-center shadow-inner">
                <ScanLine className="w-10 h-10 text-primary animate-pulse" />
              </div>
            </div>
            <div>
              <h3 className="text-2xl font-black text-gray-900 mb-2">Reading receipt...</h3>
              <p className="text-gray-500 font-medium">Extracting your groceries with AI.</p>
            </div>
          </div>
        )}

        {scannedItems && !processing && (
          <div className="space-y-6 flex-1 flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500 h-full">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-black text-gray-900 flex items-center">
                <CheckCircle2 className="w-6 h-6 mr-3 text-primary" />
                Found {scannedItems.length} items
              </h2>
              <button 
                className="text-sm font-black text-gray-400 hover:text-gray-600 transition-colors" 
                onClick={() => setScannedItems(null)}
              >
                Cancel
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto pr-2 -mr-2 space-y-4 pb-4">
              {scannedItems.length === 0 ? (
                <div className="p-12 text-center text-gray-500 bg-white border border-dashed rounded-[1.5rem] font-medium h-full flex items-center justify-center">
                  No items could be extracted from this receipt.
                </div>
              ) : (
                scannedItems.map((item, i) => (
                  <div key={i} className="bg-white border-2 border-neo-border shadow-sm rounded-[1.5rem] p-4 flex flex-col gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gray-50 rounded-xl flex items-center justify-center shrink-0">
                        <Edit3 className="w-4 h-4 text-gray-400" />
                      </div>
                      <input 
                        type="text" 
                        value={item.name} 
                        onChange={e => updateItem(i, { name: e.target.value })}
                        placeholder="Item name"
                        className="flex-1 font-black text-lg bg-transparent focus:outline-none focus:ring-0 placeholder:text-gray-300"
                      />
                      <button onClick={() => removeItem(i)} className="w-10 h-10 rounded-full bg-red-50 text-red-500 flex items-center justify-center hover:bg-red-100 transition-colors shrink-0">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="flex gap-3 pl-13">
                      <div className="flex-1 bg-gray-50 rounded-xl px-4 py-2 focus-within:ring-2 focus-within:ring-emerald-500 transition-shadow">
                        <label className="text-[10px] font-black text-gray-400 uppercase tracking-wider block mb-1">Qty</label>
                        <input 
                          type="number" 
                          value={item.quantity || ''} 
                          onChange={e => updateItem(i, { quantity: parseFloat(e.target.value) || 0 })}
                          className="w-full bg-transparent font-black text-gray-900 focus:outline-none"
                        />
                      </div>
                      <div className="flex-1 bg-gray-50 rounded-xl px-4 py-2 focus-within:ring-2 focus-within:ring-emerald-500 transition-shadow">
                        <label className="text-[10px] font-black text-gray-400 uppercase tracking-wider block mb-1">Unit</label>
                        <input 
                          type="text" 
                          value={item.unit} 
                          onChange={e => updateItem(i, { unit: e.target.value })}
                          placeholder="e.g. kg, L"
                          className="w-full bg-transparent font-black text-gray-900 focus:outline-none"
                        />
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="pt-2 mt-auto">
              <Button 
                className="w-full rounded-[1.5rem] py-7 text-lg font-black shadow-[6px_6px_0_var(--neo-shadow)] bg-primary hover:bg-primary-dark" 
                onClick={handleAddToPantry}
                disabled={adding || scannedItems.length === 0}
              >
                {adding ? 'Adding...' : `Add ${scannedItems.length} Items`}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
