import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { UserMe } from '../api/client';
import { fetchMe, login as apiLogin } from '../api/client';

type AuthState = {
  user: UserMe | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem('restbar_token');
    localStorage.removeItem('restbar_user');
    setUser(null);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('restbar_token');
    const cached = localStorage.getItem('restbar_user');
    if (cached) {
      try {
        setUser(JSON.parse(cached));
      } catch {
        /* ignore */
      }
    }
    if (!token) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then((me) => {
        setUser(me);
        localStorage.setItem('restbar_user', JSON.stringify(me));
      })
      .catch(() => logout())
      .finally(() => setLoading(false));
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiLogin(email, password);
    localStorage.setItem('restbar_token', data.access_token);
    localStorage.setItem('restbar_user', JSON.stringify(data.user));
    setUser(data.user);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, logout }),
    [user, loading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth fuera de AuthProvider');
  return ctx;
}
