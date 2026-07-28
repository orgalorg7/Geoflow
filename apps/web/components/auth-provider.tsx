"use client";

import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApiError, apiRequest } from "@/lib/api";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

interface AuthResponse {
  user: User;
  token_type: "cookie";
}

interface Registration {
  email: string;
  fullName: string;
  password: string;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: Registration) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      try {
        const currentUser = await apiRequest<User>("/auth/me");
        if (active) setUser(currentUser);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) return;
        try {
          const refreshed = await apiRequest<AuthResponse>("/auth/refresh", {
            method: "POST",
          });
          if (active) setUser(refreshed.user);
        } catch {
          if (active) setUser(null);
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void restoreSession();
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async login(email, password) {
        const result = await apiRequest<AuthResponse>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        setUser(result.user);
      },
      async register(input) {
        const result = await apiRequest<AuthResponse>("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            email: input.email,
            full_name: input.fullName,
            password: input.password,
          }),
        });
        setUser(result.user);
      },
      async logout() {
        try {
          await apiRequest<void>("/auth/logout", { method: "POST" });
        } finally {
          setUser(null);
        }
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
