import { useEffect, useState, type ReactNode } from "react";
import * as authApi from "../api/auth";
import { setAuthToken, setUnauthorizedHandler } from "../api/client";
import type { User } from "../types";
import { AuthContext } from "./AuthContext";

const TOKEN_STORAGE_KEY = "stockflow_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // No stored token means there's nothing to restore, so start "not loading" directly rather
  // than flipping true -> false on mount (avoids an extra synchronous render from the effect).
  const [isLoading, setIsLoading] = useState(() => Boolean(localStorage.getItem(TOKEN_STORAGE_KEY)));

  useEffect(() => {
    setUnauthorizedHandler(() => {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setAuthToken(null);
      setUser(null);
    });

    const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!stored) {
      return;
    }
    setAuthToken(stored);
    authApi
      .me()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setAuthToken(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const token = await authApi.login(email, password);
    localStorage.setItem(TOKEN_STORAGE_KEY, token.access_token);
    setAuthToken(token.access_token);
    setUser(await authApi.me());
  }

  async function register(email: string, password: string, fullName: string) {
    await authApi.register(email, password, fullName);
    await login(email, password);
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setAuthToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, isAdmin: user?.role === "admin", login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
