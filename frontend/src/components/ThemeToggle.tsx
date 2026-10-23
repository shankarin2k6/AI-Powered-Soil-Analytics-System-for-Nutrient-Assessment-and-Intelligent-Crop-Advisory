"use client";

import { useEffect, useState } from "react";
import Icon from "@/components/Icon";
import { t, useLang } from "@/lib/i18n";

type Theme = "light" | "dark";

/**
 * Sun / moon button. The page starts light; the choice is remembered in this browser.
 * The icon shows the theme you will switch TO (moon while light, sun while dark), like most websites.
 * layout.tsx sets data-theme before the first paint, so there is no flash of the wrong theme on reload.
 */
export default function ThemeToggle() {
  useLang();
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
  }, []);

  function toggle() {
    const next: Theme = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      /* private window: the choice just lasts until the page is closed */
    }
  }

  const label = t(theme === "light" ? "theme.to_dark" : "theme.to_light");
  return (
    <button className="theme-toggle" onClick={toggle} aria-label={label} title={label}>
      <Icon key={theme} name={theme === "light" ? "moon" : "sun"} size={22} />
    </button>
  );
}
