"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AnalysisView from "@/components/AnalysisView";
import Icon from "@/components/Icon";
import PageHead from "@/components/PageHead";
import TrendCard from "@/components/TrendCard";
import { ApiError, HistoryItem, SoilTestRecord, Trend, api, mediaUrl } from "@/lib/api";
import { ensureField } from "@/lib/session";
import { formatDate, t, useLang } from "@/lib/i18n";

const when = (iso: string) => formatDate(iso);

function LabValues({ d }: { d: SoilTestRecord }) {
  useLang();
  return (
    <dl className="values">
      <dt>N</dt><dd>{d.nitrogen}</dd>
      <dt>P</dt><dd>{d.phosphorus}</dd>
      <dt>K</dt><dd>{d.potassium}</dd>
      <dt>pH</dt><dd>{d.ph}</dd>
      {d.organic_matter != null && (<><dt>{t("test.organic_matter")}</dt><dd>{d.organic_matter}%</dd></>)}
      {d.moisture != null && (<><dt>{t("test.moisture")}</dt><dd>{d.moisture}%</dd></>)}
    </dl>
  );
}

/** `test` is the lab test saved together with this photo, if the farmer entered one. */
function Card({ item, index, test }: { item: HistoryItem; index: number; test?: SoilTestRecord }) {
  useLang();
  const style = { ["--i" as string]: Math.min(index, 8) };
  if (item.type === "image") {
    return (
      <li className="card" style={style}>
        <div className="card-head"><Icon name="camera" /><strong>{t("history.photo")}</strong></div>
        <small>{when(item.created_at)}</small>
        {test ? <LabValues d={test} /> : <p className="no-lab">{t("history.no_lab")}</p>}
        <img className="photo" src={mediaUrl(item.data.urls.normalized)} alt="" />
        {item.data.quality.warnings.map((w) => <p key={w} className="notice"><Icon name="alert" /> {t(w)}</p>)}
      </li>
    );
  }
  if (item.type === "soil_test") {
    const d = item.data;
    return (
      <li className="card" style={style}>
        <div className="card-head"><Icon name="flask" /><strong>{t("history.test")}</strong></div>
        <small>{d.tested_on ? formatDate(`${d.tested_on}T00:00`, false) : when(item.created_at)}</small>
        <LabValues d={d} />
      </li>
    );
  }
  const record = { id: item.id, field_id: 0, image_id: item.data.image_id, soil_test_id: item.data.soil_test_id,
                   model_version: item.data.model_version, created_at: item.created_at, result: item.data.result };
  return (
    <li className="card" style={style}>
      <div className="card-head"><Icon name="chart" /><strong>{t("history.analysis")}</strong></div>
      <small>{when(item.created_at)}</small>
      <AnalysisView record={record} compact />
    </li>
  );
}

export default function HistoryPage() {
  useLang();
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [trend, setTrend] = useState<Trend | null>(null);

  useEffect(() => {
    ensureField().then((id) => api.trend(id)).then(setTrend).catch(() => { /* the chart is optional */ });
    ensureField()
      .then(api.history)
      .then(setItems)
      .catch((e) => setError(t(e instanceof ApiError && e.messageKey ? e.messageKey : "error.generic")));
  }, []);

  // a lab test saved together with a photo is shown inside that photo's card, not as a separate card
  const photoIds = new Set((items ?? []).filter((i) => i.type === "image").map((i) => i.id));
  const testFor = (id: number) =>
    (items ?? []).find((i): i is Extract<HistoryItem, { type: "soil_test" }> => i.type === "soil_test" && i.data.image_id === id)?.data;
  const visible = (items ?? []).filter((i) => !(i.type === "soil_test" && i.data.image_id != null && photoIds.has(i.data.image_id)));

  return (
    <>
      <PageHead title={t("history.title")} lead={t("history.lead")} />
      {error && <p className="error" role="alert">{error}</p>}
      {trend && trend.points.length > 0 && <TrendCard trend={trend} />}
      {!error && items === null && (
        <div className="card-grid" aria-busy="true">
          <div className="skeleton" /><div className="skeleton" /><div className="skeleton" />
        </div>
      )}
      {items?.length === 0 && (
        <div className="empty">
          <p>{t("history.empty")}</p>
          <div className="empty-actions">
            <Link className="big-button primary" href="/capture"><Icon name="camera" /> {t("home.cta.photo")}</Link>
            <Link className="big-button" href="/soil-test"><Icon name="flask" /> {t("home.cta.test")}</Link>
          </div>
        </div>
      )}
      <ul className="card-grid list">
        {visible.map((item, i) => (
          <Card key={`${item.type}-${item.id}`} item={item} index={i} test={item.type === "image" ? testFor(item.id) : undefined} />
        ))}
      </ul>
    </>
  );
}
