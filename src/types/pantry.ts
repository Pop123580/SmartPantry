export interface PantryItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  category: string;
  status: 'safe' | 'expiring_soon' | 'running_low';
  risk: 'low' | 'medium' | 'high';
  expiresAt: string;
  imageUrl?: string;
}

export interface CreatePantryItemDTO {
  name: string;
  quantity: number;
  unit: string;
  category: string;
  expiresAt?: string;
  imageUrl?: string;
}
