import { PantryItem, CreatePantryItemDTO } from '../../types/pantry';

export interface PantryApi {
  getItems: () => Promise<PantryItem[]>;
  getItem: (id: string) => Promise<PantryItem>;
  addItem: (item: CreatePantryItemDTO) => Promise<PantryItem>;
  updateItem: (id: string, updates: Partial<PantryItem>) => Promise<PantryItem>;
  deleteItem: (id: string) => Promise<void>;
}
