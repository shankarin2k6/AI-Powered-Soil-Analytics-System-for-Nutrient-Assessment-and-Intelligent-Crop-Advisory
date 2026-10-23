"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ApiError, Farmer, ProfileInput, api } from "@/lib/api";
import { getLanguage } from "@/lib/i18n";

/**
 * Who is signed in. The login itself is a cookie that the browser keeps (the page cannot read it),
 * so on start the app asks the server "who am I?" (/auth/me).
 */
type State =
  | { status: "loading" }
  | { status: "signedOut" }
  | { status: "signedIn"; farmer: Farmer }
  | { status: "error" }; // the server could not be reached

type AuthContext = {
  state: State;
  signup: (name: string, phone: string, password: string) => Promise<void>;
  login: (phone: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (body: ProfileInput) => Promise<void>;
  retry: () => void;
};

const Ctx = createContext<AuthContext | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<State>({ status: "loading" });

  const check = useCallback(() => {
    setState({ status: "loading" });
    api
      .me()
      .then((farmer) => setState({ status: "signedIn", farmer }))
      .catch((e) => setState(e instanceof ApiError && e.status === 401 ? { status: "signedOut" } : { status: "error" }));
  }, []);

  useEffect(check, [check]);

  useEffect(() => {
    const expired = () => setState({ status: "signedOut" });
    window.addEventListener("auth:expired", expired);
    return () => window.removeEventListener("auth:expired", expired);
  }, []);

  const value = useMemo<AuthContext>(
    () => ({
      state,
      signup: async (name, phone, password) => setState({ status: "signedIn", farmer: await api.signup(name, phone, password, getLanguage()) }),
      login: async (phone, password) => setState({ status: "signedIn", farmer: await api.login(phone, password) }),
      logout: async () => {
        try {
          await api.logout();
        } finally {
          setState({ status: "signedOut" });
        }
      },
      updateProfile: async (body) => setState({ status: "signedIn", farmer: await api.updateProfile(body) }),
      retry: check,
    }),
    [state, check],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
