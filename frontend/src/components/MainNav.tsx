"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Icon, { IconName } from "@/components/Icon";
import { t, useLang } from "@/lib/i18n";

// One list, two looks: a bottom bar on phones and a row in the top bar on laptops (see globals.css).
// To add a screen in a later milestone, add one line here.
const ITEMS: { href: string; icon: IconName; label: string }[] = [
  { href: "/", icon: "home", label: "nav.home" },
  { href: "/capture", icon: "camera", label: "nav.photo" },
  { href: "/soil-test", icon: "flask", label: "nav.test" },
  { href: "/analysis", icon: "chart", label: "nav.analysis" },
  { href: "/history", icon: "list", label: "nav.history" },
];

export default function MainNav() {
  useLang();
  const pathname = usePathname();
  return (
    <nav className="main-nav" aria-label={t("nav.aria")}>
      {ITEMS.map((item) => (
        <Link key={item.href} href={item.href} aria-current={pathname === item.href ? "page" : undefined}>
          <Icon name={item.icon} />
          <span>{t(item.label)}</span>
        </Link>
      ))}
    </nav>
  );
}
