import { ReceiptApi } from '../../api/receiptApi';
import { apiUpload } from '../../api/client';
import type { CreatePantryItemDTO } from '../../../types/pantry';

export const fastapiReceiptApi: ReceiptApi = {
  uploadReceipt: (file: File) => apiUpload<CreatePantryItemDTO[]>('/api/receipt/upload', file),
};
