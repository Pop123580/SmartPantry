import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api/client';
import type { ShoppingItem } from '../types/shopping';

export const useShopping = () => {
  const [items, setItems] = useState<ShoppingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchItems = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.shopping.getShoppingList();
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

  const addItem = async (item: Omit<ShoppingItem, 'id'>) => {
    const newItem = await api.shopping.addItem(item);
    setItems(prev => [...prev, newItem]);
  };

  const checkout = async () => {
    await api.shopping.checkout();
    setItems([]);
  };

  return { items, loading, error, refresh: fetchItems, addItem, checkout };
};
