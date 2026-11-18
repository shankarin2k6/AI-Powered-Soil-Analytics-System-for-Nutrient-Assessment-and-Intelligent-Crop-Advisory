"use client";

import Link from "next/link";
import Icon from "@/components/Icon";
import { AnalysisRecord, ImageResult, LabRating, gradcamUrl, mediaUrl } from "@/lib/api";
import { t, useLang } from "@/lib/i18n";

/** Shows one saved analysis. `compact` is the short version used on the history page. */

const pct = (p: number) => `${Math.round(p * 100)}%`;
// older saved analyses may hold "Arid_Soil"; the dictionary uses the short name "Arid"
const soilName = (c: string) => t(`soil.class.${c.replace(/_Soil$/, "")}`);

/** Colour of a rating: ok (green), low (amber), bad (red). */
function tone(level: string): "ok" | "low" | "bad" {
  if (level === "low" || level === "acidic" || level === "alkaline") return "low";
  if (level.startsWith("strongly")) return "bad";
  return "ok";
}

function ScoreRing({ score, grade, small }: { score: number; grade: string; small?: boolean }) {
  useLang();
  return (
    <div className={`ring ${grade}${small ? " small" : ""}`} role="img" aria-label={`${score} / 100`}>
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle className="ring-track" cx="60" cy="60" r="52" pathLength={100} />
        <circle className="ring-value" cx="60" cy="60" r="52" pathLength={100} strokeDasharray={`${score} 100`} />
      </svg>
      <div className="ring-text"><strong>{Math.round(score)}</strong>{!small && <small>{t("analysis.out_of")}</small>}</div>
    </div>
  );
}

function SoilType({ image, fusion, record, onConfirm, busy }: {
  image: ImageResult; fusion: AnalysisRecord["result"]["fusion"]; record: AnalysisRecord;
  onConfirm?: (soil: string) => void; busy?: boolean;
}) {
  useLang();
  if (!image.available) return <p className="notice"><Icon name="alert" size={18} /> {t(image.reason_key)}</p>;
  const photo = record.image_id ? mediaUrl(`/api/v1/images/${record.image_id}/file?variant=normalized`) : null;
  const heat = image.has_gradcam;
  return (
    <div className="stack">
      {image.tier === "confident" || fusion.soil_class_source === "user" ? (
        <p className="soil-name"><small>{t("soil.confident")}</small>
          <strong>{soilName(fusion.soil_class ?? "")}</strong>
          {fusion.soil_class_source === "image" && <span className="pill">{pct(image.confidence)}</span>}
        </p>
      ) : image.tier === "confirm" ? (
        <div className="stack">
          <p className="notice"><Icon name="alert" size={18} /> {t("soil.confirm")}</p>
          {fusion.lab_hint && <p className="hint">{t("analysis.confirm.hint", { soil: soilName(fusion.lab_hint) })}</p>}
          {onConfirm && (
            <div className="choices" role="group" aria-label={t("analysis.confirm.pick")}>
              {image.candidates.map((c) => (
                <button key={c.soil_class} className={`big-button${c.soil_class === fusion.lab_hint ? " primary" : ""}`}
                        disabled={busy} onClick={() => onConfirm(c.soil_class)}>
                  {soilName(c.soil_class)} <span className="pill">{pct(c.probability)}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="stack">
          <p className="notice"><Icon name="alert" size={18} /> {t(image.message_key)}</p>
          <Link className="big-button" href="/capture"><Icon name="camera" /> {t("analysis.add_photo")}</Link>
        </div>
      )}
      {heat && photo && (
        <figure className="heat">
          <div className="heat-pair">
            <img className="photo" src={photo} alt="" />
            <img className="photo" src={gradcamUrl(record.id)} alt={t("analysis.heatmap")} />
          </div>
          <figcaption>{t("analysis.heatmap")}</figcaption>
        </figure>
      )}
      {fusion.notes.filter((n) => n !== "fusion.please_confirm_soil" || image.tier !== "confirm").map((n) => (
        <p key={n} className="notice"><Icon name="alert" size={18} /> {t(n)}</p>
      ))}
    </div>
  );
}

function Ratings({ rows }: { rows: LabRating[] }) {
  useLang();
  return (
    <ul className="rates list">
      {rows.map((r) => (
        <li key={r.parameter} className={`rate ${tone(r.level)}`}>
          <span className="rate-name">{r.parameter === "ph" ? "pH" : t(`test.${r.parameter}`)}</span>
          <span className="rate-value">{r.value}{r.unit ? ` ${r.unit}` : ""}</span>
          <span className="rate-label">{t(r.message_key)}</span>
        </li>
      ))}
    </ul>
  );
}

export default function AnalysisView({ record, onConfirmSoil, busy, compact }: {
  record: AnalysisRecord; onConfirmSoil?: (soil: string) => void; busy?: boolean; compact?: boolean;
}) {
  useLang();
  const r = record.result;
  const fert = r.fertilizer_signal;
  const issues = r.diagnosis.deficiencies.length + (r.diagnosis.ph_issue ? 1 : 0);

  if (compact) {
    return (
      <div className="compact-analysis">
        {r.health ? <ScoreRing score={r.health.score} grade={r.health.grade} small /> : null}
        <div className="stack tight">
          {r.health && <strong>{t(r.health.message_key)}</strong>}
          {r.fusion.soil_class && <span>{soilName(r.fusion.soil_class)}</span>}
          {r.degradation && <span className={`pill ${r.degradation.level}`}>{t(r.degradation.message_key)}</span>}
          {r.health && <small>{issues ? t("history.issues", { n: issues }) : t("diagnosis.none_found")}</small>}
          {!r.health && !r.fusion.soil_class && (
            <small>{r.image.available ? t(r.image.message_key) : t(r.image.reason_key)}</small>
          )}
          {!r.health && <small>{t("analysis.no_lab")}</small>}
        </div>
        <Link className="big-button ghost view-link" href={`/analysis?id=${record.id}`} aria-label={t("analysis.view")}>
          <span className="view-label">{t("analysis.view")}</span>
          <span className="view-arrow" aria-hidden="true"><Icon name="chevron" size={20} /></span>
        </Link>
      </div>
    );
  }

  return (
    <div className="analysis">
      {(r.health || r.degradation) && (
        <section className="panel summary">
          {r.health && (
            <div className="summary-health">
              <ScoreRing score={r.health.score} grade={r.health.grade} />
              <div className="stack tight">
                <h2>{t("analysis.section.health")}</h2>
                <p className={`grade ${r.health.grade}`}>{t(r.health.message_key)}</p>
              </div>
            </div>
          )}
          {r.degradation && (
            <div className="summary-risk stack">
              <h2>{t("analysis.section.degradation")}</h2>
              <div className={`meter ${r.degradation.level}`} role="img" aria-label={`${r.degradation.index} / 100`}>
                <span style={{ width: `${r.degradation.index}%` }} />
              </div>
              <p className={`grade ${r.degradation.level}`}>{t(r.degradation.message_key)}</p>
              {r.degradation.drivers.length > 0 && (
                <ul className="drivers list">
                  {r.degradation.drivers.map((d) => <li key={d.factor}>{t(d.message_key)}</li>)}
                </ul>
              )}
            </div>
          )}
        </section>
      )}

      <section className="panel stack">
        <h2>{t("analysis.section.type")}</h2>
        <SoilType image={r.image} fusion={r.fusion} record={record} onConfirm={onConfirmSoil} busy={busy} />
      </section>

      <section className="panel stack">
        <h2>{t("analysis.section.diagnosis")}</h2>
        {!r.lab && <p className="notice"><Icon name="alert" size={18} />
          <span>{t("analysis.no_lab")} <Link href="/soil-test">{t("analysis.add_test")}</Link></span></p>}
        {r.lab && (
          <>
            <p className="hint">{t(r.diagnosis.summary_key)}</p>
            <ul className="issues list">
              {r.diagnosis.deficiencies.map((d) => (
                <li key={d.nutrient} className="issue low">
                  <span>{t(d.message_key)}</span>
                  {d.support.includes("model") && <span className="pill ok">{t("analysis.model_agrees")}</span>}
                </li>
              ))}
              {r.diagnosis.ph_issue && (
                <li className={`issue ${tone(r.diagnosis.ph_issue.level)}`}><span>{t(r.diagnosis.ph_issue.message_key)}</span></li>
              )}
            </ul>
            <h3>{t("analysis.section.lab")}</h3>
            <Ratings rows={r.lab.ratings} />
          </>
        )}
      </section>

      <section className="panel stack">
        <h2>{t("analysis.section.fertilizer")}</h2>
        {!fert.available ? (
          <p className="hint">{t(fert.reason_key)}</p>
        ) : (
          <>
            <ul className="bars list">
              {fert.recommendations.map((f, i) => (
                <li key={f.label}>
                  <span className="bar-label">{f.label}</span>
                  <span className="bar"><span className={i === 0 ? "top" : ""} style={{ width: pct(f.probability) }} /></span>
                  <span className="bar-value">{pct(f.probability)}</span>
                </li>
              ))}
            </ul>
            {!fert.confident && <p className="notice"><Icon name="alert" size={18} /> {t("fertilizer.uncertain")}</p>}
            {fert.notes.map((n) => <p key={n} className="notice"><Icon name="alert" size={18} /> {t(n)}</p>)}
            <h3>{t("analysis.section.why")} <small>({fert.explanation.for})</small></h3>
            <ul className="shap list">
              {(() => {
                const max = Math.max(...fert.explanation.features.map((f) => Math.abs(f.contribution)), 1e-9);
                return fert.explanation.features.map((f) => (
                  <li key={f.feature}>
                    <span className="bar-label">{t(`feature.${f.feature}`)}</span>
                    <span className="bar"><span className={f.direction} style={{ width: `${(Math.abs(f.contribution) / max) * 100}%` }} /></span>
                    <span className="bar-value">{t(`analysis.why.${f.direction}`)}</span>
                  </li>
                ));
              })()}
            </ul>
          </>
        )}
      </section>

      {r.crops && (
        <section className="panel stack">
          <h2>{t("analysis.section.crops")}</h2>
          {!r.crops.available ? (
            <p className="hint">{t(r.crops.reason_key)}</p>
          ) : (
            <>
              <p className="hint">{t(r.crops.summary_key)}</p>
              <ol className="crop-list list">
                {r.crops.top.map((c, i) => (
                  <li key={c.crop} className="crop">
                    <div className="crop-head">
                      <strong>{t(`crop.${c.crop}`)}</strong>
                      <span className={`pill fit-${c.fit}`}>{t(c.message_key)}</span>
                    </div>
                    <div className="crop-bar">
                      <span className="bar"><span className={i === 0 ? "top" : ""} style={{ width: `${c.score}%` }} /></span>
                      <span className="bar-value">{Math.round(c.score)}% {t("crops.match")}</span>
                    </div>
                    <p className="crop-why">{c.reasons.map((x) => t(x.key)).join(" ")}</p>
                  </li>
                ))}
              </ol>
            </>
          )}
        </section>
      )}

      {r.warnings.length > 0 && (
        <section className="stack">
          {r.warnings.map((w, i) => <p key={i} className="notice"><Icon name="alert" size={18} /> {t(w.key)}</p>)}
        </section>
      )}
      <p className="disclaimer">{t("analysis.disclaimer")}</p>
    </div>
  );
}
