import { ShoppingApi } from '../../api/shoppingApi';
import { ShoppingItem } from '../../../types/shopping';
import { fetchApi } from '../../api/client';

export const fastapiShoppingApi: ShoppingApi = {
  getShoppingList: () => fetchApi('/api/shopping'),
  addItem: (item: Omit<ShoppingItem, 'id'>) => fetchApi('/api/shopping', { method: 'POST', body: JSON.stringify(item) }),
  removeItem: (id: string) => fetchApi(`/api/shopping/${id}`, { method: 'DELETE' }),
  checkout: () => fetchApi('/api/shopping/checkout', { method: 'POST' })
};
