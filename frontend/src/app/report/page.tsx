"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import AnalysisView from "@/components/AnalysisView";
import Brand from "@/components/Brand";
import Icon from "@/components/Icon";
import { AnalysisRecord, ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, t, useLang } from "@/lib/i18n";

/**
 * Printable soil report for one saved analysis. "Download PDF" opens the browser's print dialog (choose
 * "Save as PDF"). The browser draws the text itself, so Hindi, Kannada and Tamil letters join correctly,
 * which many server-side PDF libraries get wrong. Print styles are at the end of globals.css.
 */
function Report() {
  useLang();
  const id = Number(useSearchParams().get("id")) || 0;
  const { state } = useAuth();
  const [record, setRecord] = useState<AnalysisRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) { setError("analysis.nothing_to_analyze"); return; }
    api.getAnalysis(id).then(setRecord).catch((e) => setError(e instanceof ApiError && e.messageKey ? e.messageKey : "error.generic"));
  }, [id]);

  // always print on a white page, even when the dark theme is on
  useEffect(() => {
    const root = document.documentElement;
    let before: string | undefined;
    const onBefore = () => { before = root.dataset.theme; delete root.dataset.theme; };
    const onAfter = () => { if (before) root.dataset.theme = before; };
    window.addEventListener("beforeprint", onBefore);
    window.addEventListener("afterprint", onAfter);
    return () => { window.removeEventListener("beforeprint", onBefore); window.removeEventListener("afterprint", onAfter); };
  }, []);

  const farmer = state.status === "signedIn" ? state.farmer : null;
  return (
    <div className="report">
      <div className="report-actions no-print">
        <Link className="big-button ghost" href={id ? `/analysis?id=${id}` : "/history"}><Icon name="chevron" size={18} /> {t("report.back")}</Link>
        <button className="big-button primary" onClick={() => window.print()} disabled={!record}>
          <Icon name="save" size={20} /> {t("report.download")}
        </button>
      </div>
      <p className="hint no-print">{t("report.hint")}</p>

      {error && <p className="error" role="alert">{t(error)}</p>}
      {!error && !record && <div className="skeleton" aria-busy="true" />}
      {record && (
        <article className="report-sheet">
          <header className="report-head">
            <Brand />
            <h1>{t("report.title")}</h1>
            <dl className="report-meta">
              {farmer && <><dt>{t("report.for")}</dt><dd>{farmer.name}</dd></>}
              {farmer?.phone && <><dt>{t("profile.phone")}</dt><dd>{farmer.phone}</dd></>}
              {farmer?.address && <><dt>{t("profile.address")}</dt><dd>{farmer.address}</dd></>}
              <dt>{t("report.date")}</dt><dd>{formatDate(record.created_at)}</dd>
              <dt>{t("report.number")}</dt><dd>#{record.id}</dd>
            </dl>
          </header>
          <AnalysisView record={record} />
          <footer className="report-foot">{t("report.generated", { date: formatDate(record.created_at, false) })}</footer>
        </article>
      )}
    </div>
  );
}

export default function ReportPage() {
  useLang();
  return <Suspense fallback={<div className="skeleton" aria-busy="true" />}><Report /></Suspense>;
}
