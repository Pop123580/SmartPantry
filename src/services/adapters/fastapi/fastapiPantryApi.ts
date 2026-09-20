import { PantryApi } from '../../api/pantryApi';
import { CreatePantryItemDTO, PantryItem } from '../../../types/pantry';
import { fetchApi } from '../../api/client';

export const fastapiPantryApi: PantryApi = {
  getItems: () => fetchApi('/api/pantry'),
  getItem: (id: string) => fetchApi(`/api/pantry/${id}`),
  addItem: (item: CreatePantryItemDTO) => fetchApi('/api/pantry', { method: 'POST', body: JSON.stringify(item) }),
  updateItem: (id: string, updates: Partial<PantryItem>) => fetchApi(`/api/pantry/${id}`, { method: 'PATCH', body: JSON.stringify(updates) }),
  deleteItem: (id: string) => fetchApi(`/api/pantry/${id}`, { method: 'DELETE' })
};
