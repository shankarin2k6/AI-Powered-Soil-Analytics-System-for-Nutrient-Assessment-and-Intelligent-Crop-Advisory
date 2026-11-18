"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Icon from "@/components/Icon";
import { t, useLang } from "@/lib/i18n";

/** Round arrow that appears after the farmer has scrolled a good way down and takes them back to the top. */
export default function ScrollToTop({ after = 400 }: { after?: number }) {
  useLang();
  const [show, setShow] = useState(false);

  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > after);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [after]);

  const up = () => {
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: calm ? "auto" : "smooth" });
  };

  // drawn on <body>: the page animates with a transform, which would otherwise trap a fixed button inside it
  return createPortal(
    <button type="button" className={`to-top${show ? " show" : ""}`} onClick={up} aria-label={t("scroll.top")} title={t("scroll.top")} tabIndex={show ? 0 : -1}>
      <Icon name="arrowup" size={22} />
    </button>,
    document.body,
  );
}
