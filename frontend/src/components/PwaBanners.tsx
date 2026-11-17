"use client";

import { useEffect, useState } from "react";
import Icon from "@/components/Icon";
import { t, useLang } from "@/lib/i18n";
import { registerServiceWorker, useInstall, useOnline } from "@/lib/pwa";

/** Registers the service worker, tells the farmer when the phone is offline and offers "Add to home screen". */
export default function PwaBanners({ clearTools = false }: { clearTools?: boolean }) {
  useLang();
  const online = useOnline();
  const { canInstall, showIosHint, install } = useInstall();
  const [dismissed, setDismissed] = useState(true);   // hidden until we know the saved choice (avoids a flash)

  useEffect(() => {
    registerServiceWorker();
    try { setDismissed(localStorage.getItem("install-dismissed") === "1"); } catch { setDismissed(false); }
  }, []);

  const hide = () => { setDismissed(true); try { localStorage.setItem("install-dismissed", "1"); } catch { /* private mode */ } };

  return (
    <>
      {!online && (
        <p className={`pwa-banner offline${clearTools ? " clear-tools" : ""}`} role="status">
          <Icon name="alert" size={18} /> <span>{t("pwa.offline")}</span>
        </p>
      )}
      {online && !dismissed && (canInstall || showIosHint) && (
        <div className={`pwa-banner install${clearTools ? " clear-tools" : ""}`} role="region" aria-label={t("pwa.install")}>
          <Icon name="phone" size={20} />
          <span>{canInstall ? t("pwa.install_text") : t("pwa.ios_hint")}</span>
          {canInstall && <button type="button" className="big-button primary" onClick={install}>{t("pwa.install")}</button>}
          <button type="button" className="icon-button" onClick={hide} aria-label={t("pwa.dismiss")}><Icon name="close" size={18} /></button>
        </div>
      )}
    </>
  );
}
