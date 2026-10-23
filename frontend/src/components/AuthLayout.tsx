"use client";

import Brand from "@/components/Brand";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import SoilProfile from "@/components/SoilProfile";
import ThemeToggle from "@/components/ThemeToggle";
import { t, useLang } from "@/lib/i18n";

/** Login and signup: a soil picture beside the form on laptops, a short banner above it on phones. */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  useLang();
  return (
    <div className="auth">
      <div className="auth-tools">
        <LanguageSwitcher />
        <ThemeToggle />
      </div>
      <aside className="auth-art">
        <Brand />
        <p className="auth-tagline">{t("auth.tagline")}</p>
        <SoilProfile className="auth-svg" />
      </aside>
      <section className="auth-form">
        <div className="auth-card">{children}</div>
      </section>
    </div>
  );
}
