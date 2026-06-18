import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { AuthUser } from "../api/types";

interface AuthState {
  user: AuthUser | null;
  token: string | null;
}

interface AuthContextValue extends AuthState {
  login: (user: AuthUser, token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function loadFromStorage(): AuthState {
  try {
    const token = localStorage.getItem("ts_token");
    const raw = localStorage.getItem("ts_user");
    if (token && raw) {
      return { token, user: JSON.parse(raw) };
    }
  } catch {}
  return { token: null, user: null };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(loadFromStorage);

  const login = useCallback((user: AuthUser, token: string) => {
    localStorage.setItem("ts_token", token);
    localStorage.setItem("ts_user", JSON.stringify(user));
    setState({ user, token });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("ts_token");
    localStorage.removeItem("ts_user");
    setState({ user: null, token: null });
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...state, login, logout, isAuthenticated: !!state.user }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
