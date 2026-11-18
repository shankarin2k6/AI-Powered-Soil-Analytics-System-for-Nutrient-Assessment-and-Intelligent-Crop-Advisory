"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Icon from "@/components/Icon";
import { t, useLang } from "@/lib/i18n";

/** Round "i" button in the top bar that opens the About page, like the info button in most apps. */
export default function AboutLink() {
  useLang();
  const here = usePathname() === "/about";
  return (
    <Link href="/about" className={`theme-toggle about-link${here ? " on" : ""}`} aria-label={t("about.open")} title={t("about.open")}
          aria-current={here ? "page" : undefined}>
      <Icon name="info" size={20} />
    </Link>
  );
}
