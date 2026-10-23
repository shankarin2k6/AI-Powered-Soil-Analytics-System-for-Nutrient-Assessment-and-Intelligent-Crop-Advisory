"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import AnalysisView from "@/components/AnalysisView";
import Icon from "@/components/Icon";
import PageHead from "@/components/PageHead";
import PhotoPicker from "@/components/PhotoPicker";
import { AnalysisRecord, AnalyzeInput, ApiError, ImageRecord, ModelStatus, api } from "@/lib/api";
import { ensureField } from "@/lib/session";
import { t, useLang } from "@/lib/i18n";

const CROP_FIELDS = ["crop_type", "growth_stage", "season"] as const;

/** The value sent to the API is the model's own name (for example "Kharif"); the label is what the farmer reads. */
function optionLabel(field: string, value: string): string {
  const key = `option.${field}.${value}`;
  const label = t(key);
  return label === key ? value.replace(/_/g, " ") : label;
}

function AnalysisScreen() {
  useLang();
  const savedId = Number(useSearchParams().get("id")) || undefined;
  const [record, setRecord] = useState<AnalysisRecord | null>(null);
  const [loading, setLoading] = useState(!!savedId);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ key: string; empty: boolean } | null>(null);
  const [options, setOptions] = useState<ModelStatus["fertilizer_options"]>({});
  const [crop, setCrop] = useState<Record<string, string>>({});
  const [images, setImages] = useState<ImageRecord[] | null>(null);     // newest first
  const [withLab, setWithLab] = useState<Set<number>>(new Set());       // photos that have lab values saved with them
  const [selected, setSelected] = useState<number | null>(null);

  const fail = (e: unknown) => {
    const key = e instanceof ApiError && e.messageKey ? e.messageKey : "error.generic";
    setError({ key, empty: key === "analysis.nothing_to_analyze" });
  };

  useEffect(() => {
    api.modelStatus().then((s) => setOptions(s.fertilizer_options)).catch(() => {});
    if (savedId) {
      api.getAnalysis(savedId).then(setRecord).catch(fail).finally(() => setLoading(false));
      return;
    }
    ensureField()
      .then((fieldId) => Promise.all([api.listImages(fieldId), api.listSoilTests(fieldId)]))
      .then(([imgs, tests]) => {
        setImages(imgs);
        setWithLab(new Set(tests.flatMap((x) => (x.image_id != null ? [x.image_id] : []))));
        setSelected(imgs[0]?.id ?? null);                    // the newest photo is pre-selected
      })
      .catch(() => setImages([]));
  }, [savedId]);

  function choose(id: number) {
    if (id === selected) return;
    setSelected(id);
    setRecord(null);                                         // the old result belongs to another photo
    setError(null);
  }

  async function run(confirmed?: string) {
    setBusy(true);
    setError(null);
    try {
      const body: AnalyzeInput = { ...(Object.fromEntries(Object.entries(crop).filter(([, v]) => v)) as AnalyzeInput) };
      if (confirmed) body.confirmed_soil_class = confirmed;
      if (selected != null) body.image_id = selected;       // exactly the photo the farmer sees ticked
      setRecord(await api.analyze(await ensureField(), body));
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }

  const hasOptions = CROP_FIELDS.some((f) => options[f]?.length);

  return (
    <>
      <PageHead title={t("analysis.title")} lead={t("analysis.lead")} />
      <div className="stack">
        {!savedId && images && <PhotoPicker images={images} selected={selected} withLab={withLab} onSelect={choose} />}
        {!savedId && (
          <div className="panel stack">
            {hasOptions && (
              <details className="crop-details">
                <summary>{t("analysis.crop.title")}</summary>
                <p className="hint">{t("analysis.crop.hint")}</p>
                <div className="form-grid">
                  {CROP_FIELDS.map((f) => (
                    <label key={f} className="field">
                      <span className="label">{t(`analysis.crop.${f}`)}</span>
                      <select value={crop[f] ?? ""} onChange={(e) => setCrop({ ...crop, [f]: e.target.value })}>
                        <option value="">{t("analysis.crop.choose")}</option>
                        {(options[f] ?? []).map((o) => <option key={o} value={o}>{optionLabel(f, o)}</option>)}
                      </select>
                    </label>
                  ))}
                </div>
              </details>
            )}
            <button className="big-button primary" onClick={() => run()} disabled={busy}>
              <Icon name="chart" /> {busy ? t("analysis.running") : record ? t("analysis.rerun") : t(selected != null ? "analysis.run_selected" : "analysis.run")}
            </button>
          </div>
        )}

        {error && (
          <div className={error.empty ? "empty" : undefined}>
            <p className={error.empty ? undefined : "error"} role="alert">{t(error.key)}</p>
            {error.empty && (
              <div className="empty-actions">
                <Link className="big-button primary" href="/capture"><Icon name="camera" /> {t("analysis.add_photo")}</Link>
                <Link className="big-button" href="/soil-test"><Icon name="flask" /> {t("analysis.add_test")}</Link>
              </div>
            )}
          </div>
        )}
        {loading && <div className="skeleton" aria-busy="true" />}
        {record && (
          <Link className="big-button ghost report-link" href={`/report?id=${record.id}`}>
            <Icon name="save" size={20} /> {t("report.open")}
          </Link>
        )}
        {record && <AnalysisView record={record} onConfirmSoil={run} busy={busy} />}
      </div>
    </>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div className="skeleton" />}>
      <AnalysisScreen />
    </Suspense>
  );
}
