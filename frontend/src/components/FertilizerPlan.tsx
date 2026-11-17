"use client";

import { useEffect, useRef, useState } from "react";
import Icon from "@/components/Icon";
import { AnalysisRecord, ApiError, FertilizerPlan as Plan, PlanItem, api } from "@/lib/api";
import { t, useLang } from "@/lib/i18n";

/** Step-by-step fertiliser plan: pick the crop, where it is now and the field size; the server sends per-acre amounts. */

const STAGES = ["before", "early", "middle", "late"] as const;
const HECTARE_IN_ACRES = 2.471;

/** Farmers read whole kilograms; small amounts keep one half so "0.5 kg" is not shown as "1 kg". */
function kg(perAcre: number, scale: number): string {
  const v = perAcre * scale;
  const shown = v >= 10 ? Math.round(v) : Math.max(0.5, Math.round(v * 2) / 2);
  return t("plan.kg", { kg: shown.toLocaleString() });
}

export default function FertilizerPlan({ record, onSettled }: { record: AnalysisRecord; onSettled?: () => void }) {
  useLang();
  const settled = useRef(onSettled);        // the printable report waits for the first answer (plan or error) before it allows printing
  settled.current = onSettled;
  const r = record.result;
  const [crops, setCrops] = useState<string[]>([]);
  const topCrop = r.crops?.available ? r.crops.top[0]?.crop : undefined;
  const [crop, setCrop] = useState<string>("");
  const [stage, setStage] = useState<(typeof STAGES)[number]>("before");
  const [area, setArea] = useState("1");
  const [unit, setUnit] = useState<"acre" | "hectare">("acre");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);

  // the choice is kept per result, so the printable report shows the plan the farmer was looking at
  const storeKey = `plan-choice-${record.id}`;
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storeKey) ?? "null");
      if (saved?.crop) setCrop(saved.crop);
      if (STAGES.includes(saved?.stage)) setStage(saved.stage);
      if (typeof saved?.area === "string") setArea(saved.area);
      if (saved?.unit === "acre" || saved?.unit === "hectare") setUnit(saved.unit);
    } catch { /* no saved choice */ }
  }, [storeKey]);
  useEffect(() => {
    if (!crop) return;
    try { localStorage.setItem(storeKey, JSON.stringify({ crop, stage, area, unit })); } catch { /* private mode */ }
  }, [storeKey, crop, stage, area, unit]);

  useEffect(() => {
    api.planCrops().then((c) => {
      setCrops(c.crops);
      setCrop((cur) => cur || (topCrop && c.crops.includes(topCrop) ? topCrop : c.crops[0]));
    }).catch(() => { setError("plan.error"); settled.current?.(); });
  }, [topCrop]);

  useEffect(() => {
    if (!crop) return;
    let current = true;
    setError(null);
    api.fertilizerPlan(record.id, crop, stage)
      .then((p) => { if (current) { setPlan(p); settled.current?.(); } })
      .catch((e) => { if (current) { setError(e instanceof ApiError && e.messageKey ? e.messageKey : "plan.error"); settled.current?.(); } });
    return () => { current = false; };
  }, [record.id, crop, stage]);

  if (!r.lab) return null;                                    // a plan needs lab values
  const acres = Math.max(0, parseFloat(area.replace(",", ".")) || 0) * (unit === "hectare" ? HECTARE_IN_ACRES : 1);
  const scale = acres || 1;                                    // an empty size shows the per-acre amounts
  const fert = r.fertilizer_signal;
  const modelPick = fert.available && fert.recommendations.length ? fert.recommendations[0].label : null;

  const Items = ({ items }: { items: PlanItem[] }) => (
    <ul className="plan-items list">
      {items.map((i) => (
        <li key={i.product}><span>{t(`plan.product.${i.product}`)}</span><strong>{kg(i.kg, scale)}</strong></li>
      ))}
    </ul>
  );

  return (
    <section className="panel stack plan">
      <h2>{t("plan.title")}</h2>
      <p className="hint">{t("plan.intro")}</p>

      <p className="plan-print-line">{crop && t("plan.print_line", { crop: t(`crop.${crop}`), stage: t(`plan.stage.${stage}`), area: area || "1", unit: t(`plan.unit.${unit}`) })}</p>
      <div className="plan-controls">
        <label className="field"><span>{t("plan.crop")}</span>
          <select value={crop} onChange={(e) => setCrop(e.target.value)}>
            {crops.map((c) => <option key={c} value={c}>{t(`crop.${c}`)}</option>)}
          </select>
        </label>
        <label className="field"><span>{t("plan.stage")}</span>
          <select value={stage} onChange={(e) => setStage(e.target.value as (typeof STAGES)[number])}>
            {STAGES.map((s) => <option key={s} value={s}>{t(`plan.stage.${s}`)}</option>)}
          </select>
        </label>
        <div className="field plan-area"><span>{t("plan.area")}</span>
          <div className="plan-area-row">
            <input type="number" inputMode="decimal" min="0" step="0.5" value={area} onChange={(e) => setArea(e.target.value)}
                   aria-label={t("plan.area")} />
            <select value={unit} onChange={(e) => setUnit(e.target.value as "acre" | "hectare")} aria-label={t("plan.area")}>
              <option value="acre">{t("plan.unit.acre")}</option>
              <option value="hectare">{t("plan.unit.hectare")}</option>
            </select>
          </div>
        </div>
      </div>

      {modelPick && <p className="hint">{t("plan.model_note", { name: modelPick })}</p>}
      {error && <p className="error" role="alert">{t(error)}</p>}
      {!plan && !error && <div className="skeleton" aria-busy="true" />}

      {plan && !plan.available && <p className="hint">{t(plan.reason_key)}</p>}
      {plan && plan.available && !error && (
        <div className="stack">
          <p className="plan-nutrients">{t("plan.nutrients", {
            n: Math.round(plan.nutrients.n * scale),
            p: Math.round(plan.nutrients.p2o5 * scale), k: Math.round(plan.nutrients.k2o * scale) })}</p>
          <ul className="plan-adjust list">
            {plan.adjustments.map((a) => <li key={a.nutrient}>{t(`plan.adjust.${a.level}`, { nutrient: t(`test.${a.nutrient}`) })}</li>)}
          </ul>

          <h3>{t("plan.buy")}</h3>
          <Items items={plan.shopping} />

          <ol className="plan-steps list">
            {plan.steps.map((s) => (
              <li key={s.id} className={`plan-step ${s.state ?? ""}`}>
                <div className="plan-step-head">
                  <strong>{t(s.title_key, s.title_params)}</strong>
                  {s.state && <span className={`pill plan-${s.state}`}>{t(`plan.state.${s.state}`)}</span>}
                </div>
                <small className="plan-when"><Icon name="calendar" size={14} /> {t(s.timing_key, s.timing_params)}</small>
                <Items items={s.items} />
                <p className="plan-how">{t(s.how_key)}</p>
              </li>
            ))}
          </ol>

          <h3>{t("plan.note.title")}</h3>
          <ul className="plan-notes list">
            {plan.notes.map((n) => <li key={n}>{t(n)}</li>)}
            {["plan.note.1", "plan.note.2", "plan.note.3"].map((n) => <li key={n}>{t(n)}</li>)}
          </ul>
          <p className="notice"><Icon name="alert" size={18} /> {t("plan.disclaimer")}</p>
        </div>
      )}
    </section>
  );
}
