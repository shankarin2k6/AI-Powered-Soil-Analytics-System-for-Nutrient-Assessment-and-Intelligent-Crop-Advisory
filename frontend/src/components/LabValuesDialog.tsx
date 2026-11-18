"use client";

import { createPortal } from "react-dom";
import { FormEvent, useEffect, useRef, useState } from "react";
import Icon from "@/components/Icon";
import { FIELDS } from "@/components/SoilTestForm";
import { ApiError, SoilTestInput, SoilTestRecord, api } from "@/lib/api";
import { formatDate, t, useLang } from "@/lib/i18n";

const show = (n: number | null | undefined) => (n == null ? "" : String(n));

/**
 * Pop-up with the lab values saved with one photo. The farmer can read them and change them;
 * a photo without lab values gets an empty form, and saving creates the test for that photo.
 */
export default function LabValuesDialog({ fieldId, imageId, imageDate, test, onClose, onSaved }: {
  fieldId: number; imageId: number; imageDate: string; test: SoilTestRecord | null;
  onClose: () => void; onSaved: (saved: SoilTestRecord) => void;
}) {
  useLang();
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(FIELDS.map((f) => [f.name, show(test?.[f.name as keyof SoilTestRecord] as number | null)])));
  const [testedOn, setTestedOn] = useState(test?.tested_on ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const first = useRef<HTMLInputElement>(null);

  useEffect(() => {
    first.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";                 // the page behind does not scroll
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = old; };
  }, [onClose]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const found: Record<string, string> = {};
    const body: Record<string, unknown> = {};
    for (const f of FIELDS) {
      const raw = (values[f.name] ?? "").trim().replace(",", ".");
      if (raw === "") { if (f.required) found[f.name] = t("test.error.required"); continue; }
      const n = Number(raw);
      if (!Number.isFinite(n) || n < f.min || n > f.max) found[f.name] = t("test.error.range", { min: f.min, max: f.max });
      else body[f.name] = n;
    }
    if (testedOn && testedOn > new Date().toISOString().slice(0, 10)) found.tested_on = t("test.error.future");
    setErrors(found);
    if (Object.keys(found).length) return;
    if (testedOn) body.tested_on = testedOn;

    setSaving(true);
    try {
      const saved = test
        ? await api.updateSoilTest(test.id, body as Omit<SoilTestInput, "image_id">)
        : await api.createSoilTest(fieldId, { ...(body as SoilTestInput), image_id: imageId });
      onSaved(saved);
    } catch (err) {
      setFormError(t(err instanceof ApiError && err.messageKey ? err.messageKey : "error.generic"));
    } finally {
      setSaving(false);
    }
  }

  // drawn on <body>: the page animates with a transform, which would otherwise trap a fixed pop-up inside it
  return createPortal(
    <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="lab-title">
        <div className="modal-head">
          <div>
            <h2 id="lab-title">{t("lab.title")}</h2>
            <p className="hint">{t("lab.for_photo", { date: formatDate(imageDate) })}</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label={t("lab.close")}><Icon name="close" size={22} /></button>
        </div>

        {!test && <p className="notice"><Icon name="alert" size={18} /> <span>{t("lab.empty")}</span></p>}

        <form className="stack" onSubmit={onSubmit} noValidate>
          <div className="form-grid">
            {FIELDS.map((f, i) => (
              <label key={f.name} className="field">
                <span className="label">
                  {f.chip ? <span className="chip">{f.chip}</span> : <Icon name={f.icon!} size={18} />} {t(`test.${f.name}`)}
                  {!f.required && <small> ({t("test.optional")})</small>}
                </span>
                <span className="input-row">
                  <input
                    ref={i === 0 ? first : undefined}
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
              <input type="date" value={testedOn} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setTestedOn(e.target.value)} />
              {errors.tested_on && <span className="error" role="alert">{errors.tested_on}</span>}
            </label>
          </div>
          {formError && <p className="error" role="alert">{formError}</p>}
          <button className="big-button primary" type="submit" disabled={saving}>
            <Icon name="save" /> {saving ? t("test.saving") : t(test ? "test.save" : "lab.save")}
          </button>
        </form>
      </div>
    </div>,
    document.body,
  );
}
