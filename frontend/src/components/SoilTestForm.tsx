"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import Icon, { IconName } from "@/components/Icon";
import { ApiError, SoilTestInput, api } from "@/lib/api";
import { ensureField } from "@/lib/session";
import { t, useLang } from "@/lib/i18n";

/**
 * To add or change a lab value, edit this list (and the backend schema SoilTestCreate).
 * The limits must match the backend; the backend is the final check.
 */
export type FieldDef = {
  name: keyof SoilTestInput;
  chip?: string;
  icon?: IconName;
  unit: string;
  min: number;
  max: number;
  required: boolean;
};
export const FIELDS: FieldDef[] = [
  { name: "nitrogen", chip: "N", unit: "mg/kg", min: 0, max: 500, required: true },
  { name: "phosphorus", chip: "P", unit: "mg/kg", min: 0, max: 500, required: true },
  { name: "potassium", chip: "K", unit: "mg/kg", min: 0, max: 500, required: true },
  { name: "ph", chip: "pH", unit: "0–14", min: 0, max: 14, required: true },
  { name: "organic_matter", icon: "leaf", unit: "%", min: 0, max: 100, required: false },
  { name: "moisture", icon: "drop", unit: "%", min: 0, max: 100, required: false },
];

type Props = { imageId?: number };

export default function SoilTestForm({ imageId }: Props) {
  useLang();
  const [values, setValues] = useState<Record<string, string>>({});
  const [testedOn, setTestedOn] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  function validate(): Record<string, string> {
    const found: Record<string, string> = {};
    for (const f of FIELDS) {
      const raw = (values[f.name] ?? "").trim().replace(",", ".");
      if (raw === "") {
        if (f.required) found[f.name] = t("test.error.required");
        continue;
      }
      const n = Number(raw);
      if (!Number.isFinite(n) || n < f.min || n > f.max) {
        found[f.name] = t("test.error.range", { min: f.min, max: f.max });
      }
    }
    if (testedOn && testedOn > new Date().toISOString().slice(0, 10)) found.tested_on = t("test.error.future");
    return found;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length) return;

    const body: Record<string, unknown> = {};
    for (const f of FIELDS) {
      const raw = (values[f.name] ?? "").trim().replace(",", ".");
      if (raw !== "") body[f.name] = Number(raw);
    }
    if (testedOn) body.tested_on = testedOn;
    if (imageId) body.image_id = imageId;

    setSaving(true);
    try {
      const fieldId = await ensureField();
      await api.createSoilTest(fieldId, body as SoilTestInput);
      setSaved(true);
    } catch (err) {
      setFormError(t(err instanceof ApiError && err.messageKey ? err.messageKey : "error.generic"));
    } finally {
      setSaving(false);
    }
  }

  if (saved) {
    return (
      <div className="stack">
        <p className="success"><span className="check-badge"><Icon name="check" size={18} /></span>{t("test.saved")}</p>
        <Link className="big-button primary" href="/history"><Icon name="list" /> {t("history.view")}</Link>
        <button className="big-button" onClick={() => { setValues({}); setTestedOn(""); setSaved(false); }}>
          <Icon name="flask" /> {t("test.another")}
        </button>
      </div>
    );
  }

  return (
    <form className="stack" onSubmit={onSubmit} noValidate>
      {imageId && <p className="notice"><Icon name="camera" size={18} /> {t("test.linked_photo")}</p>}

      <div className="form-grid">
      {FIELDS.map((f) => (
        <label key={f.name} className="field">
          <span className="label">
            {f.chip ? <span className="chip">{f.chip}</span> : <Icon name={f.icon!} size={18} />} {t(`test.${f.name}`)}
            {!f.required && <small> ({t("test.optional")})</small>}
          </span>
          <span className="input-row">
            <input
              type="text" inputMode="decimal" autoComplete="off"
              value={values[f.name] ?? ""}
              onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
              aria-invalid={!!errors[f.name]}
            />
            <span className="unit">{f.unit}</span>
          </span>
          {errors[f.name] && <span className="error" role="alert">{errors[f.name]}</span>}
        </label>
      ))}

      <label className="field">
        <span className="label"><Icon name="calendar" size={18} /> {t("test.tested_on")} <small>({t("test.optional")})</small></span>
        <input type="date" value={testedOn} max={new Date().toISOString().slice(0, 10)}
               onChange={(e) => setTestedOn(e.target.value)} />
        {errors.tested_on && <span className="error" role="alert">{errors.tested_on}</span>}
      </label>
      </div>

      {formError && <p className="error" role="alert">{formError}</p>}
      <button className="big-button primary" type="submit" disabled={saving}>
        <Icon name="save" /> {saving ? t("test.saving") : t("test.save")}
      </button>
    </form>
  );
}
