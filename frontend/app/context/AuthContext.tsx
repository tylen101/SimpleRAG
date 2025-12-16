'use client';

import React, {
  createContext,
  useState,
  useEffect,
  useContext,
  useCallback,
  ReactNode,
} from 'react';

type User = { user_id: number; display_name: string };
type AuthContextType = {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fetchUser = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Unauthorized');
      const data = await res.json();
      setUser(data);
    } catch (err) {
      console.warn('No active session');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };
  /* --- Fetch current user on mount --- */
  useEffect(() => {
    fetchUser();
  }, []);

  /* --- Shared auth helper --- */
  const handleAuth = useCallback(
    async (
      endpoint: 'login' | 'register',
      username: string,
      password: string
    ) => {
      setError(null);
      setLoading(true);

      const controller = new AbortController();

      try {
        const res = await fetch(`${API_BASE}/auth/${endpoint}`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ username, password }),
          signal: controller.signal,
        });

        let data: any = null;
        try {
          data = await res.json();
        } catch {
          data = null;
        }

        if (!res.ok) {
          const msg =
            data?.detail ||
            (res.status === 400
              ? 'Bad request — possible duplicate username'
              : res.status === 401
              ? 'Invalid username or password'
              : `Server error (${res.status})`);
          throw new Error(msg);
        }

        if (data?.user) {
          setUser(data.user);
          setError(null);
        } else {
          // Fallback fetch /auth/me if not included in response
          const meRes = await fetch(`${API_BASE}/auth/me`, {
            credentials: 'include',
          });
          if (meRes.ok) setUser(await meRes.json());
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        console.error('Auth error:', err);
        setUser(null);
        setError(err.message || 'Authentication failed');
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /* --- Actions --- */
  const login = (u: string, p: string) => handleAuth('login', u, p);
  const register = (u: string, p: string) => handleAuth('register', u, p);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (e) {
      console.warn('Logout request failed');
    }
    setUser(null);
  }, []);

  const value: AuthContextType = {
    user,
    login,
    register,
    logout,
    isAuthenticated: !!user,
    loading,
    error,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/* --- Hook --- */
export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
