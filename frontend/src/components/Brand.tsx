"use client";

import Link from "next/link";
import Icon from "@/components/Icon";
import { t, useLang } from "@/lib/i18n";

export default function Brand() {
  useLang();
  return (
    <Link href="/" className="brand">
      <span className="brand-mark"><Icon name="sprout" size={20} /></span>
      <span>{t("app.title")}</span>
    </Link>
  );
}
