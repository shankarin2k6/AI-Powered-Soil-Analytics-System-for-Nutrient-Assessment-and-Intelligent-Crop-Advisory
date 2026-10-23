"use client";

import { Trend } from "@/lib/api";
import { formatDate, t, useLang } from "@/lib/i18n";

const W = 320, H = 150, PAD = { l: 34, r: 12, t: 12, b: 26 };

/**
 * Soil health score of every saved analysis as a line. With 3 or more analyses over at least 2 weeks it also says
 * whether the soil is improving, steady or declining and gives a rough 90-day estimate (the dotted extension).
 */
export default function TrendCard({ trend }: { trend: Trend }) {
  useLang();
  const pts = trend.points;
  if (pts.length === 0) return null;
  const times = pts.map((p) => new Date(p.date).getTime());
  const t0 = times[0], t1 = times[times.length - 1];
  const span = Math.max(t1 - t0, 1);
  const x = (ms: number) => PAD.l + ((ms - t0) / span) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - v / 100) * (H - PAD.t - PAD.b);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${x(times[i]).toFixed(1)} ${y(p.health_score).toFixed(1)}`).join(" ");
  const last = pts[pts.length - 1];
  const tone = trend.direction === "declining" ? "bad" : trend.direction === "improving" ? "good" : "";

  return (
    <section className="panel stack trend">
      <div className="trend-head">
        <h2>{t("trend.title")}</h2>
        <small>{t("trend.count", { n: pts.length })}</small>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t("trend.chart_aria")} className="trend-svg">
        {[0, 50, 100].map((g) => (
          <g key={g}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(g)} y2={y(g)} className="trend-grid" />
            <text x={PAD.l - 6} y={y(g) + 4} textAnchor="end" className="trend-tick">{g}</text>
          </g>
        ))}
        {pts.length > 1 && <path d={line} className="trend-line" fill="none" />}
        {pts.map((p, i) => <circle key={p.analysis_id} cx={x(times[i])} cy={y(p.health_score)} r={4.5} className="trend-dot" />)}
        <text x={PAD.l} y={H - 6} className="trend-tick">{formatDate(pts[0].date, false)}</text>
        {pts.length > 1 && <text x={W - PAD.r} y={H - 6} textAnchor="end" className="trend-tick">{formatDate(last.date, false)}</text>}
      </svg>
      <p className="hint">{t("trend.score")}: <strong>{last.health_score}</strong></p>
      <p className={`trend-msg ${tone}`}>{t(trend.message_key)}</p>
      {trend.enough_data && trend.change_per_month != null && trend.estimate_90d != null && (
        <p className="hint">
          {t("trend.change", { n: `${trend.change_per_month > 0 ? "+" : ""}${trend.change_per_month}` })}. {t("trend.estimate", { n: Math.round(trend.estimate_90d) })}
        </p>
      )}
    </section>
  );
}
