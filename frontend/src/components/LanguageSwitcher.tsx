"use client";

import { useEffect, useRef, useState } from "react";
import Icon from "@/components/Icon";
import { LANGUAGES, setLanguage, t, useLang } from "@/lib/i18n";

/**
 * Translate button (like Google Translate): tap it and the list of languages opens; tap a language and the whole
 * app switches at once. Used on the login page and in the top bar. The choice is remembered in this browser and,
 * once logged in, on the farmer's profile (see LanguageSync in AppShell).
 */
export default function LanguageSwitcher() {
  const lang = useLang();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function choose(code: (typeof LANGUAGES)[number]["code"]) {
    setLanguage(code);
    setOpen(false);
  }

  return (
    <div className="lang" ref={root}>
      <button className="lang-button" onClick={() => setOpen((o) => !o)} aria-haspopup="listbox" aria-expanded={open}
              aria-label={t("lang.change")} title={t("lang.change")}>
        <Icon name="translate" size={22} />
      </button>
      {open && (
        <ul className="lang-menu" role="listbox" aria-label={t("lang.choose")}>
          {LANGUAGES.map((l) => (
            <li key={l.code} role="presentation">
              <button role="option" aria-selected={l.code === lang} lang={l.code}
                      className={l.code === lang ? "selected" : undefined} onClick={() => choose(l.code)}>
                <span className="lang-native">{l.native}</span>
                {l.code !== "en" && <small>{l.english}</small>}
                {l.code === lang && <Icon name="check" size={18} />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
