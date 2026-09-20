import { ShoppingItem } from '../../types/shopping';

export interface ShoppingApi {
  getShoppingList: () => Promise<ShoppingItem[]>;
  addItem: (item: Omit<ShoppingItem, 'id'>) => Promise<ShoppingItem>;
  removeItem: (id: string) => Promise<void>;
  checkout: () => Promise<void>;
}
