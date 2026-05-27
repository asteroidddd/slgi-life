// AuthContext — global auth state for SPEC step 9.
//
// Backed by Django session cookie (axios `withCredentials: true`).
// On mount we call GET /api/users/me; 200 → set user, 401 → user stays null.
//
// Usage:
//   <QueryClientProvider>
//     <AuthProvider>
//       <BrowserRouter><App /></BrowserRouter>
//     </AuthProvider>
//   </QueryClientProvider>
//
//   const { user, isLoading, login, register, logout, refresh } = useAuth();
//
// Notes:
//   - No localStorage / sessionStorage. Auth lives only in this context +
//     the server-side session cookie.
//   - The context exposes the raw API errors (axios) so callers can show the
//     Korean `detail` from the backend directly.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import axios from 'axios';

import {
  getMe,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
} from '@/lib/api';
import type {
  LoginPayload,
  MeResponse,
  RegisterPayload,
} from '@/types/api';

export interface AuthContextValue {
  /** Current user or null when logged out. */
  user: MeResponse | null;
  /** True until the boot-time `getMe()` resolves (success or 401). */
  isLoading: boolean;
  /** Sign in. Throws on failure (caller handles UI). */
  login: (payload: LoginPayload) => Promise<MeResponse>;
  /** Register + auto-login. Falls back to a follow-up login if the backend
   *  ever stops auto-logging in. Throws on failure.
   */
  register: (payload: RegisterPayload) => Promise<MeResponse>;
  /** Sign out. Idempotent. */
  logout: () => Promise<void>;
  /** Re-fetch GET /api/users/me, e.g. after a profile patch. */
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
      // 401 = not logged in. Anything else is a network error; either way we
      // can't claim a session.
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        setUser(null);
        return null;
      }
      setUser(null);
      return null;
    }
  }, []);

  // Boot-time session restore. Runs exactly once.
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

  const login = useCallback(async (payload: LoginPayload): Promise<MeResponse> => {
    const me = await apiLogin(payload);
    setUser(me);
    return me;
  }, []);

  const register = useCallback(async (payload: RegisterPayload): Promise<MeResponse> => {
    try {
      const me = await apiRegister(payload);
      setUser(me);
      return me;
    } catch (err) {
      // If register ever stops auto-logging in (backend policy change), try
      // a follow-up login so the caller still ends up authenticated.
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        const me = await apiLogin({
          username: payload.username,
          password: payload.password,
        });
        setUser(me);
        return me;
      }
      throw err;
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiLogout();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, login, register, logout, refresh }),
    [user, isLoading, login, register, logout, refresh]
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
