"use client";

import { useEffect, useRef, useState } from "react";
import Icon from "@/components/Icon";
import { t, useLang } from "@/lib/i18n";
import { useInstall } from "@/lib/pwa";

/** Small install icon in the top bar. It stays available after the install banner has been closed. */
export default function InstallButton() {
  useLang();
  const { canInstall, showIosHint, install } = useInstall();
  const [hint, setHint] = useState(false);
  const box = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!hint) return;
    const close = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setHint(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [hint]);

  if (!canInstall && !showIosHint) return null;   // already installed, or this browser cannot install the app

  return (
    <span className="install-wrap" ref={box}>
      <button
        type="button"
        className="theme-toggle install-button"
        title={t("pwa.install")}
        aria-label={t("pwa.install")}
        onClick={() => (canInstall ? install() : setHint((h) => !h))}
      >
        <Icon name="phone" size={20} />
      </button>
      {hint && <p className="install-hint" role="status">{t("pwa.ios_hint")}</p>}
    </span>
  );
}
