import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api/client';
import type { PantryItem, CreatePantryItemDTO } from '../types/pantry';

export const usePantry = () => {
  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchItems = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.pantry.getItems();
      setItems(data);
      setError(null);
    } catch (err: any) {
      setError(err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const addItem = async (item: CreatePantryItemDTO) => {
    const newItem = await api.pantry.addItem(item);
    setItems(prev => [...prev, newItem]);
    return newItem;
  };

  const deleteItem = async (id: string) => {
    await api.pantry.deleteItem(id);
    setItems(prev => prev.filter(i => i.id !== id));
  };

  return { items, loading, error, refresh: fetchItems, addItem, deleteItem };
};
