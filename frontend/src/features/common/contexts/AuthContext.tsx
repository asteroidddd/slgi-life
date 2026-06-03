// AuthContext — global auth state backed by Django session cookie.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import axios from 'axios';

import {
  getMe,
  logout as apiLogout,
} from '@/features/common/lib/api';
import type {
  MeResponse,
} from '@/features/common/types/api';

export interface AuthContextValue {
  user: MeResponse | null;
  isLoading: boolean;
  logout: () => Promise<void>;
  refresh: () => Promise<MeResponse | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refresh = useCallback(async (): Promise<MeResponse | null> => {
    try {
      const me = await getMe();
      setUser(me);
      return me;
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        setUser(null);
        return null;
      }
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await refresh();
      if (!cancelled) setIsLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiLogout();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, logout, refresh }),
    [user, isLoading, logout, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
}
