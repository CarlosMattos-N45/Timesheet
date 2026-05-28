import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { STORAGE } from "@/api/client";
import { postLogin, postLogout } from "@/api/auth";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  terceiroId: string | null;
  expiresAt: number | null;
}

interface AuthContextValue extends AuthState {
  isAuthenticated: boolean;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readState(): AuthState {
  return {
    accessToken: sessionStorage.getItem(STORAGE.accessToken),
    refreshToken: sessionStorage.getItem(STORAGE.refreshToken),
    terceiroId: sessionStorage.getItem(STORAGE.terceiroId),
    expiresAt: Number(sessionStorage.getItem(STORAGE.expiresAt)) || null,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(readState);

  useEffect(() => {
    const onLogout = () =>
      setState({ accessToken: null, refreshToken: null, terceiroId: null, expiresAt: null });
    window.addEventListener("ts:auth-logout", onLogout);
    return () => window.removeEventListener("ts:auth-logout", onLogout);
  }, []);

  const login = useCallback(async (email: string, senha: string) => {
    const r = await postLogin(email, senha);
    const expAt = Date.now() + r.expires_in * 1000;
    sessionStorage.setItem(STORAGE.accessToken, r.access_token);
    sessionStorage.setItem(STORAGE.refreshToken, r.refresh_token);
    sessionStorage.setItem(STORAGE.terceiroId, r.terceiro_id);
    sessionStorage.setItem(STORAGE.expiresAt, String(expAt));
    setState({
      accessToken: r.access_token,
      refreshToken: r.refresh_token,
      terceiroId: r.terceiro_id,
      expiresAt: expAt,
    });
  }, []);

  const logout = useCallback(() => {
    const rtok = sessionStorage.getItem(STORAGE.refreshToken);
    if (rtok) {
      // best-effort; ignora falha
      postLogout(rtok).catch(() => {});
    }
    sessionStorage.removeItem(STORAGE.accessToken);
    sessionStorage.removeItem(STORAGE.refreshToken);
    sessionStorage.removeItem(STORAGE.terceiroId);
    sessionStorage.removeItem(STORAGE.expiresAt);
    setState({ accessToken: null, refreshToken: null, terceiroId: null, expiresAt: null });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, isAuthenticated: Boolean(state.accessToken), login, logout }),
    [state, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const v = useContext(AuthContext);
  if (!v) throw new Error("useAuth deve ser usado dentro de <AuthProvider>");
  return v;
}
