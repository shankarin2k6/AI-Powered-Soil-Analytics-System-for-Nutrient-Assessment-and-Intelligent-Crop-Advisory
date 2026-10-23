"use client";

import { useRouter, usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import AuthLayout from "@/components/AuthLayout";
import Brand from "@/components/Brand";
import Icon from "@/components/Icon";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import MainNav from "@/components/MainNav";
import ProfileMenu from "@/components/ProfileMenu";
import ThemeToggle from "@/components/ThemeToggle";
import { AuthProvider, useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { hasSavedLanguage, initLanguage, setLanguage, t, useLang } from "@/lib/i18n";

const PUBLIC_PAGES = ["/login", "/signup"]; // everything else needs a login

function Splash({ children }: { children?: React.ReactNode }) {
  useLang();
  return (
    <div className="splash">
      <span className="brand-mark pulse"><Icon name="sprout" size={26} /></span>
      {children ?? <p className="hint">{t("loading")}</p>}
    </div>
  );
}

/**
 * Keeps the language in step with the account.
 * - First start in this browser: use the language saved on the account (or the one chosen on the login page).
 * - Later: when the farmer picks another language, save it on the account (best effort).
 */
function LanguageSync() {
  const { state } = useAuth();
  const lang = useLang();
  const synced = useRef<string | null>(null);
  const farmer = state.status === "signedIn" ? state.farmer : null;

  useEffect(() => {
    if (!farmer) { synced.current = null; return; }
    if (synced.current === null) {
      synced.current = farmer.language;
      if (!hasSavedLanguage()) { setLanguage(farmer.language as never); return; }
    }
    if (lang !== synced.current) {
      synced.current = lang;
      api.setLanguage(lang).catch(() => { /* the app still works in the chosen language on this phone */ });
    }
  }, [farmer, lang]);
  return null;
}

function Shell({ children }: { children: React.ReactNode }) {
  useLang();
  const { state, logout, retry } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isPublic = PUBLIC_PAGES.includes(pathname);

  // pick up the remembered language once, in the browser, before anything else is drawn
  useEffect(() => { initLanguage(); }, []);

  // send visitors to the right place
  useEffect(() => {
    if (state.status === "signedOut" && !isPublic) router.replace("/login");
    if (state.status === "signedIn" && isPublic) router.replace("/");
  }, [state.status, isPublic, router]);

  if (state.status === "loading") return <Splash />;
  if (state.status === "error")
    return (
      <Splash>
        <div className="stack center">
          <p className="error" role="alert">{t("auth.session_error")}</p>
          <button className="big-button" onClick={retry}>{t("auth.retry")}</button>
        </div>
      </Splash>
    );
  if ((state.status === "signedOut" && !isPublic) || (state.status === "signedIn" && isPublic)) return <Splash />; // redirecting

  if (state.status === "signedOut") return <AuthLayout>{children}</AuthLayout>;

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <Brand />
          <MainNav />
          <span className="header-user">
            <LanguageSwitcher />
            <ThemeToggle />
            <ProfileMenu farmer={state.farmer} onLogout={logout} />
          </span>
        </div>
      </header>
      <main className="page">
        {/* keyed by path so every page change plays the short fade-in */}
        <div key={pathname} className="page-in">{children}</div>
      </main>
    </>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <LanguageSync />
      <Shell>{children}</Shell>
    </AuthProvider>
  );
}
