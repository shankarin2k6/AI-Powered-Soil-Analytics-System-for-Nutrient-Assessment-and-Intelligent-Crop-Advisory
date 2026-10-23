"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import PageHead from "@/components/PageHead";
import SoilTestForm from "@/components/SoilTestForm";
import { t, useLang } from "@/lib/i18n";

function Form() {
  const imageId = Number(useSearchParams().get("image")) || undefined;
  return <SoilTestForm imageId={imageId} />;
}

export default function SoilTestPage() {
  useLang();
  return (
    <div className="narrow">
      <PageHead title={t("test.title")} lead={t("test.intro")} />
      <div className="panel">
        <Suspense fallback={<div className="skeleton" style={{ height: 160 }} />}>
          <Form />
        </Suspense>
      </div>
    </div>
  );
}
