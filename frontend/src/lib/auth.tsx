"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ApiError, Farmer, ProfileInput, api } from "@/lib/api";
import { getLanguage } from "@/lib/i18n";
import { clearOfflineData, rememberFarmer, rememberedFarmer } from "@/lib/pwa";

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
      .then((farmer) => { rememberFarmer(farmer); setState({ status: "signedIn", farmer }); })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) { setState({ status: "signedOut" }); return; }
        // no connection: open the app for the farmer who was signed in on this phone (pages saved earlier still work)
        const saved = rememberedFarmer<Farmer>();
        setState(saved ? { status: "signedIn", farmer: saved } : { status: "error" });
      });
  }, []);

  useEffect(check, [check]);

  useEffect(() => {
    const expired = () => { clearOfflineData(); setState({ status: "signedOut" }); };
    window.addEventListener("auth:expired", expired);
    return () => window.removeEventListener("auth:expired", expired);
  }, []);

  const value = useMemo<AuthContext>(
    () => ({
      state,
      signup: async (name, phone, password) => { await clearOfflineData(); const farmer = await api.signup(name, phone, password, getLanguage()); rememberFarmer(farmer); setState({ status: "signedIn", farmer }); },
      login: async (phone, password) => { await clearOfflineData(); const farmer = await api.login(phone, password); rememberFarmer(farmer); setState({ status: "signedIn", farmer }); },
      logout: async () => {
        try {
          await api.logout();
        } finally {
          await clearOfflineData();     // saved results belong to the farmer who just left
          setState({ status: "signedOut" });
        }
      },
      updateProfile: async (body) => { const farmer = await api.updateProfile(body); rememberFarmer(farmer); setState({ status: "signedIn", farmer }); },
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
