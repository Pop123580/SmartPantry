export interface ShoppingItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  reason: string;
  inInventory: boolean;
  imageUrl?: string;
}
