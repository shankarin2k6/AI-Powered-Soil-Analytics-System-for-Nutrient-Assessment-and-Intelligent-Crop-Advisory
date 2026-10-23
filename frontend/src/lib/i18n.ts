/**
 * All on-screen text goes through t("some.key").
 *
 * Four languages: English (the master list), Hindi, Kannada and Tamil. A key missing from a language falls back
 * to English, so a half-translated file never shows raw keys. The API also returns message keys
 * (for example "image.blurry") that resolve in the same files.
 *
 * The current language lives in this small store. Components call useLang() once at the top (it re-renders them
 * when the language changes) and then use t() as before. The choice is remembered in this browser and, for a
 * logged-in farmer, saved on their profile (see lib/auth.tsx).
 */
import { useSyncExternalStore } from "react";
import en from "@/messages/en.json";
import hi from "@/messages/hi.json";
import kn from "@/messages/kn.json";
import ta from "@/messages/ta.json";

export type Lang = "en" | "hi" | "kn" | "ta";

/** `native` is always written in its own script so a person can find their language even if the page is in another one. */
export const LANGUAGES: { code: Lang; native: string; english: string }[] = [
  { code: "en", native: "English", english: "English" },
  { code: "hi", native: "हिन्दी", english: "Hindi" },
  { code: "kn", native: "ಕನ್ನಡ", english: "Kannada" },
  { code: "ta", native: "தமிழ்", english: "Tamil" },
];

const DICTIONARIES: Record<Lang, Record<string, string>> = { en, hi, kn, ta };
const STORAGE_KEY = "lang";
const LOCALES: Record<Lang, string> = { en: "en-IN", hi: "hi-IN", kn: "kn-IN", ta: "ta-IN" };

export const isLang = (value: unknown): value is Lang => typeof value === "string" && value in DICTIONARIES;

let current: Lang = "en";
const listeners = new Set<() => void>();

function readSaved(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (isLang(saved)) return saved;
  } catch { /* storage blocked: start in English */ }
  return "en";
}

/** Called once in the browser, before the first render that matters (see LanguageSync in AppShell). */
export function initLanguage() {
  const saved = readSaved();
  if (saved !== current) setLanguage(saved, false);
}

export function hasSavedLanguage(): boolean {
  try { return isLang(localStorage.getItem(STORAGE_KEY)); } catch { return false; }
}

export function setLanguage(lang: Lang, remember = true) {
  if (!isLang(lang)) return;
  current = lang;
  if (typeof document !== "undefined") document.documentElement.lang = lang;
  if (remember) {
    try { localStorage.setItem(STORAGE_KEY, lang); } catch { /* the choice lasts until the page closes */ }
  }
  listeners.forEach((l) => l());
}

export const getLanguage = (): Lang => current;

/** Re-renders the calling component whenever the language changes. Call it at the top of every component that uses t(). */
export function useLang(): Lang {
  return useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => { listeners.delete(cb); }; },
    () => current,
    () => "en",
  );
}

export function t(key: string, params?: Record<string, string | number>): string {
  let text = DICTIONARIES[current][key] ?? en[key as keyof typeof en] ?? key;
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      text = text.split(`{${name}}`).join(String(value));
    }
  }
  return text;
}

/** True when a translation exists for this key (used for optional labels such as crop names). */
export const hasKey = (key: string) => key in DICTIONARIES[current] || key in en;

/** Dates and times in the chosen language, for example "21 अक्तू॰, 11:24 am". */
export function formatDate(iso: string, withTime = true): string {
  const opts: Intl.DateTimeFormatOptions = withTime
    ? { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }
    : { day: "numeric", month: "short", year: "numeric" };
  return new Date(iso).toLocaleString(LOCALES[current], opts);
}
