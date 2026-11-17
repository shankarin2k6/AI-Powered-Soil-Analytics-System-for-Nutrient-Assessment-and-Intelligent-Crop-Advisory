"use client";

import { useSyncExternalStore } from "react";

/** Install-to-home-screen and offline helpers. The service worker itself is public/sw.js. */

const DATA_CACHE = "soil-data-v1";   // must match public/sw.js
const FARMER_KEY = "soil-farmer";

/** The last signed-in farmer is kept on this phone so the app can open without a connection (cleared on logout). */
export function rememberFarmer(farmer: unknown) {
  try { localStorage.setItem(FARMER_KEY, JSON.stringify(farmer)); } catch { /* private mode */ }
}
export function rememberedFarmer<T>(): T | null {
  try { const raw = localStorage.getItem(FARMER_KEY); return raw ? (JSON.parse(raw) as T) : null; } catch { return null; }
}

export function registerServiceWorker() {
  // only in the production build: a service worker in `next dev` would keep serving old pages
  if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
  navigator.serviceWorker.register("/sw.js").catch(() => { /* the app works without it */ });
}

/** Saved results belong to one farmer: delete them on logout, on login and when the session expires. */
export async function clearOfflineData() {
  try { localStorage.removeItem(FARMER_KEY); } catch { /* private mode */ }
  try { Object.keys(localStorage).filter((k) => k.startsWith("plan-choice-")).forEach((k) => localStorage.removeItem(k)); } catch { /* private mode */ }
  try { await caches.delete(DATA_CACHE); } catch { /* no cache support */ }
}

const subscribe = (cb: () => void) => {
  window.addEventListener("online", cb);
  window.addEventListener("offline", cb);
  return () => { window.removeEventListener("online", cb); window.removeEventListener("offline", cb); };
};
export const useOnline = (): boolean => useSyncExternalStore(subscribe, () => navigator.onLine, () => true);

type InstallEvent = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };

/* The browser fires "beforeinstallprompt" once, early. It is kept here (not in a component) so the install button
   still works when it appears later, for example after the farmer logs in. */
let installEvent: InstallEvent | null = null;
let installed = false;
const installListeners = new Set<() => void>();
const notifyInstall = () => installListeners.forEach((cb) => cb());

if (typeof window !== "undefined") {
  installed = window.matchMedia("(display-mode: standalone)").matches || (navigator as { standalone?: boolean }).standalone === true;
  window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); installEvent = e as InstallEvent; notifyInstall(); });
  window.addEventListener("appinstalled", () => { installed = true; installEvent = null; notifyInstall(); });
}

const subscribeInstall = (cb: () => void) => { installListeners.add(cb); return () => { installListeners.delete(cb); }; };
const canInstallNow = () => !installed && installEvent !== null;
const iosNow = () => !installed && /iphone|ipad|ipod/i.test(navigator.userAgent);   // iOS has no install button for web apps

export function useInstall() {
  const canInstall = useSyncExternalStore(subscribeInstall, canInstallNow, () => false);
  const showIosHint = useSyncExternalStore(subscribeInstall, iosNow, () => false);
  return {
    canInstall,
    showIosHint,
    install: async () => {
      const ev = installEvent;
      if (!ev) return;
      await ev.prompt();
      await ev.userChoice;
      installEvent = null;
      notifyInstall();
    },
  };
}
