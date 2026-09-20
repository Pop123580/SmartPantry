import { fastapiPantryApi } from '../adapters/fastapi/fastapiPantryApi';
import { fastapiRecipeApi } from '../adapters/fastapi/fastapiRecipeApi';
import { fastapiShoppingApi } from '../adapters/fastapi/fastapiShoppingApi';
import { fastapiReceiptApi } from '../adapters/fastapi/fastapiReceiptApi';

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
export const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true';

const TOKEN_KEY = 'smartpantry_token';

export const tokenStore = {
  get(): string | null {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
    window.dispatchEvent(new Event('smartpantry:auth-changed'));
  },
  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event('smartpantry:auth-changed'));
  },
};

export class ApiError extends Error {
  status: number;
  payload: unknown;
  constructor(status: number, message: string, payload?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

async function extractError(response: Response): Promise<ApiError> {
  let message = `${response.status} ${response.statusText}`;
  let payload: unknown;
  try {
    payload = await response.json();
    const detail = (payload as { detail?: unknown })?.detail;
    if (typeof detail === 'string') message = detail;
    else if (detail && typeof detail === 'object' && 'message' in detail) {
      message = String((detail as { message: unknown }).message);
    }
  } catch { /* keep default */ }
  return new ApiError(response.status, message, payload);
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const { auth = true, ...requestOptions } = options;

  if (isDemoMode && !endpoint.startsWith('/api/auth')) {
    await new Promise(resolve => setTimeout(resolve, 300));
    if (endpoint.includes('/api/pantry')) return [] as T;
    if (endpoint.includes('/api/recipes/recommended')) return [] as T;
    if (endpoint.includes('/api/shopping')) return [] as T;
    return null as T;
  }

  const headers = new Headers(requestOptions.headers);
  if (!headers.has('Content-Type') && requestOptions.body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }

  if (auth) {
    const token = tokenStore.get();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${endpoint}`, { ...requestOptions, headers });

  if (res.status === 401 && auth) tokenStore.clear();
  if (res.status === 204) return null as T;
  if (!res.ok) throw await extractError(res);
  return (await res.json()) as T;
}

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  return apiFetch<T>(endpoint, options);
}

export async function apiUpload<T>(endpoint: string, file: File): Promise<T> {
  const token = tokenStore.get();
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (res.status === 401) tokenStore.clear();
  if (!res.ok) throw await extractError(res);
  return (await res.json()) as T;
}

export const api = {
  pantry: fastapiPantryApi,
  recipes: fastapiRecipeApi,
  shopping: fastapiShoppingApi,
  receipt: fastapiReceiptApi,
};
