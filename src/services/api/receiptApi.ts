import { CreatePantryItemDTO } from '../../types/pantry';

export interface ReceiptApi {
  uploadReceipt: (file: File) => Promise<CreatePantryItemDTO[]>;
}
