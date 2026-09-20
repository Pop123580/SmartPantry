import { useCallback, useEffect, useMemo, useState } from 'react';
import type { User } from '../types/user';
import { apiFetch, tokenStore } from '../services/api/client';

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

async function authenticate(
  endpoint: '/api/auth/login' | '/api/auth/register',
  payload: Record<string, string>
): Promise<User> {
  const response = await apiFetch<AuthResponse>(endpoint, {
    method: 'POST',
    body: JSON.stringify(payload),
    auth: false,
  });
  tokenStore.set(response.access_token);
  return response.user;
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      const token = tokenStore.get();
      if (!token) {
        if (!cancelled) setIsLoading(false);
        return;
      }
      try {
        const me = await apiFetch<User>('/api/auth/me');
        if (!cancelled) setUser(me);
      } catch {
        tokenStore.clear();
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    bootstrap();
    const onAuthChanged = () => {
      if (!tokenStore.get()) setUser(null);
    };
    window.addEventListener('smartpantry:auth-changed', onAuthChanged);
    return () => {
      cancelled = true;
      window.removeEventListener('smartpantry:auth-changed', onAuthChanged);
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      setUser(await authenticate('/api/auth/login', { email, password }));
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      return false;
    }
  }, []);

  const signup = useCallback(async (name: string, email: string, password: string) => {
    setError(null);
    try {
      setUser(await authenticate('/api/auth/register', { name, email, password }));
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signup failed');
      return false;
    }
  }, []);

  const googleLogin = useCallback(async (credential: string) => {
  setError(null);

  try {
    const response = await apiFetch<AuthResponse>('/api/auth/google', {
      method: 'POST',
      body: JSON.stringify({ credential }),
      auth: false,
    });

    tokenStore.set(response.access_token);
    setUser(response.user);

    return true;
  } catch (err) {
    setError(
      err instanceof Error
        ? err.message
        : 'Google authentication failed'
    );
    return false;
  }
}, []);

  const logout = useCallback(async () => {
    try {
      if (tokenStore.get()) await apiFetch('/api/auth/logout', { method: 'POST' });
    } catch { /* client-side token removal still completes logout */ }
    tokenStore.clear();
    setUser(null);
  }, []);

  return useMemo(() => ({
  user,
  isLoading,
  error,
  isAuthenticated: !!user,
  login,
  signup,
  googleLogin,
  logout,
}), [user, isLoading, error, login, signup, googleLogin, logout]);
}