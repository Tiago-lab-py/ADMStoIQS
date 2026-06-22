import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { api, AuthUser } from './api';

type AuthState = {
  token: string | null;
  user: AuthUser | null;
  loading: boolean;
  login: (usuario: string, senha: string) => Promise<void>;
  logout: () => void;
  canExport: boolean;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('admstoiqs.token'));
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    if (!token) {
      setLoading(false);
      setUser(null);
      return;
    }

    api
      .me(token)
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('admstoiqs.token');
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [token]);

  const value = useMemo<AuthState>(
    () => ({
      token,
      user,
      loading,
      canExport: user?.perfil === 'admin' || user?.perfil === 'gestor',
      login: async (usuario: string, senha: string) => {
        const response = await api.login(usuario, senha);
        localStorage.setItem('admstoiqs.token', response.access_token);
        setToken(response.access_token);
        setUser({
          usuario: response.usuario,
          nome_usuario: response.nome_usuario,
          perfil: response.perfil
        });
      },
      logout: () => {
        localStorage.removeItem('admstoiqs.token');
        setToken(null);
        setUser(null);
      }
    }),
    [loading, token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider.');
  }
  return value;
}
