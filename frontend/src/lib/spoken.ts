import type { AnalysisRecord } from "@/lib/api";
import { t } from "@/lib/i18n";

/** The sentences read aloud for one analysis, in the current language. Kept short: farmers listen, they do not read. */
export function spokenSummary(record: AnalysisRecord): string {
  const r = record.result;
  const parts: string[] = [t("voice.s.intro")];
  if (r.health) parts.push(t("voice.s.health", { score: Math.round(r.health.score), grade: t(r.health.message_key) }));
  if (r.fusion.soil_class) parts.push(t("voice.s.type", { soil: t(`soil.class.${r.fusion.soil_class.replace(/_Soil$/, "")}`) }));
  if (r.degradation) parts.push(t("voice.s.degradation", { level: t(r.degradation.message_key) }));
  if (r.health) {
    const issues = [...r.diagnosis.deficiencies.map((d) => t(d.message_key)), ...(r.diagnosis.ph_issue ? [t(r.diagnosis.ph_issue.message_key)] : [])];
    parts.push(issues.length ? t("voice.s.issues", { list: issues.join(" ") }) : t("diagnosis.none_found"));
  }
  const fert = r.fertilizer_signal;
  if (fert.available && fert.recommendations.length) parts.push(t("voice.s.fertilizer", { name: fert.recommendations[0].label }));
  if (r.crops?.available && r.crops.top.length) {
    parts.push(t("voice.s.crops", { list: r.crops.top.slice(0, 3).map((c) => t(`crop.${c.crop}`)).join(", ") }));
  }
  parts.push(t("voice.s.disclaimer"));
  return parts.join(" ");
}
