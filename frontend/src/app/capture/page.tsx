"use client";

import PageHead from "@/components/PageHead";
import PhotoCapture from "@/components/PhotoCapture";
import { t, useLang } from "@/lib/i18n";

export default function CapturePage() {
  useLang();
  return (
    <div className="narrow">
      <PageHead title={t("capture.title")} lead={t("capture.lead")} />
      <div className="panel"><PhotoCapture /></div>
    </div>
  );
}
