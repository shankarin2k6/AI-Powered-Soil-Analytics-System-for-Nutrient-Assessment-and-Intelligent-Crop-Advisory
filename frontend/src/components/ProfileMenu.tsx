"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import Icon from "@/components/Icon";
import { ApiError, Farmer } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { normalizePhone } from "@/lib/phone";
import { t, useLang } from "@/lib/i18n";

/**
 * The avatar button in the top bar. It opens a small panel with the farmer's details, an "Edit profile"
 * button (the same panel turns into the edit form) and "Log out". On phones the panel is a sheet under the
 * top bar; on laptops it hangs below the button.
 */
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

type Values = { name: string; phone: string; email: string; address: string };
const valuesOf = (f: Farmer): Values => ({ name: f.name, phone: f.phone ?? "", email: f.email ?? "", address: f.address ?? "" });

function Row({ icon, label, value }: { icon: "phone" | "mail" | "pin"; label: string; value?: string | null }) {
  useLang();
  return (
    <div className="profile-row">
      <Icon name={icon} size={18} />
      <div>
        <small>{label}</small>
        {value ? <p>{value}</p> : <p className="profile-empty">{t("profile.not_set")}</p>}
      </div>
    </div>
  );
}

export default function ProfileMenu({ farmer, onLogout }: { farmer: Farmer; onLogout: () => void }) {
  useLang();
  const { updateProfile } = useAuth();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  const [values, setValues] = useState<Values>(valuesOf(farmer));
  const [errors, setErrors] = useState<Partial<Record<keyof Values, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const initial = farmer.name.trim().charAt(0).toUpperCase() || "?";

  const close = () => { setOpen(false); setEditing(false); setSaved(false); setErrors({}); setFormError(null); };

  useEffect(close, [pathname]);                      // leaving the page closes the menu
  useEffect(() => {
    if (!open) return;
    const outside = (e: MouseEvent | TouchEvent) => { if (root.current && !root.current.contains(e.target as Node)) close(); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    document.addEventListener("mousedown", outside);
    document.addEventListener("touchstart", outside);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", outside);
      document.removeEventListener("touchstart", outside);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  function startEdit() {
    setValues(valuesOf(farmer));
    setErrors({});
    setFormError(null);
    setSaved(false);
    setEditing(true);
  }

  function validate(): typeof errors {
    const found: typeof errors = {};
    if (!values.name.trim()) found.name = t("profile.error.name");
    if (!normalizePhone(values.phone)) found.phone = t("profile.error.phone");
    if (values.email.trim() && !EMAIL.test(values.email.trim())) found.email = t("profile.error.email");
    if (values.address.length > 300) found.address = t("profile.error.address");
    return found;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length) return;
    setSaving(true);
    try {
      await updateProfile({ ...values, name: values.name.trim(), phone: normalizePhone(values.phone)! });
      setEditing(false);
      setSaved(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) setErrors({ phone: t("profile.error.phone_taken") });
      else setFormError(t(err instanceof ApiError && err.messageKey ? err.messageKey : "error.generic"));
    } finally {
      setSaving(false);
    }
  }

  const set = (k: keyof Values) => (e: { target: { value: string } }) => setValues({ ...values, [k]: e.target.value });

  return (
    <div className="profile" ref={root}>
      <button className="profile-button" onClick={() => (open ? close() : setOpen(true))}
              aria-expanded={open} aria-haspopup="true" aria-label={t("profile.open")}>
        <span className="avatar" aria-hidden="true">{initial}</span>
        <span className="user-name">{farmer.name}</span>
        <span className="profile-chevron" aria-hidden="true"><Icon name="chevron" size={18} /></span>
      </button>

      {open && (
        <>
          <div className="profile-backdrop" aria-hidden="true" onClick={close} />
          <div className="profile-panel" role="dialog" aria-label={t("profile.title")}>
            <button className="profile-x" onClick={close} aria-label={t("profile.close")}><Icon name="close" size={20} /></button>

            {!editing ? (
              <div className="stack">
                <div className="profile-id">
                  <span className="avatar big" aria-hidden="true">{initial}</span>
                  <div>
                    <strong>{farmer.name}</strong>
                    <small>{t("profile.title")}</small>
                  </div>
                </div>
                {saved && <p className="success"><span className="check-badge"><Icon name="check" size={16} /></span>{t("profile.saved")}</p>}
                <div className="profile-rows">
                  <Row icon="phone" label={t("profile.phone")} value={farmer.phone} />
                  <Row icon="mail" label={t("profile.email")} value={farmer.email} />
                  <Row icon="pin" label={t("profile.address")} value={farmer.address} />
                </div>
                <button className="big-button" onClick={startEdit}><Icon name="edit" size={20} /> {t("profile.edit")}</button>
                <button className="big-button ghost" onClick={onLogout}><Icon name="logout" size={20} /> {t("auth.logout")}</button>
              </div>
            ) : (
              <form className="stack" onSubmit={onSubmit} noValidate>
                <h2 className="profile-title">{t("profile.edit.title")}</h2>

                <label className="field">
                  <span className="label"><Icon name="user" size={18} /> {t("profile.name")}</span>
                  <input type="text" autoComplete="name" value={values.name} onChange={set("name")} aria-invalid={!!errors.name} />
                  {errors.name && <span className="error" role="alert">{errors.name}</span>}
                </label>

                <label className="field">
                  <span className="label"><Icon name="phone" size={18} /> {t("profile.phone")}</span>
                  <input type="tel" inputMode="numeric" autoComplete="tel" value={values.phone} onChange={set("phone")} aria-invalid={!!errors.phone} />
                  {errors.phone && <span className="error" role="alert">{errors.phone}</span>}
                </label>

                <label className="field">
                  <span className="label"><Icon name="mail" size={18} /> {t("profile.email")} <small>({t("profile.optional")})</small></span>
                  <input type="text" inputMode="email" autoComplete="email" autoCapitalize="none" placeholder={t("profile.email.hint")}
                         value={values.email} onChange={set("email")} aria-invalid={!!errors.email} />
                  {errors.email && <span className="error" role="alert">{errors.email}</span>}
                </label>

                <label className="field">
                  <span className="label"><Icon name="pin" size={18} /> {t("profile.address")} <small>({t("profile.optional")})</small></span>
                  <textarea rows={3} autoComplete="street-address" placeholder={t("profile.address.hint")}
                            value={values.address} onChange={set("address")} aria-invalid={!!errors.address} />
                  {errors.address && <span className="error" role="alert">{errors.address}</span>}
                </label>

                {formError && <p className="error" role="alert">{formError}</p>}
                <div className="profile-actions">
                  <button className="big-button primary" type="submit" disabled={saving}>
                    <Icon name="save" size={20} /> {saving ? t("profile.saving") : t("profile.save")}
                  </button>
                  <button className="big-button ghost" type="button" onClick={() => { setEditing(false); setErrors({}); setFormError(null); }}>
                    {t("profile.cancel")}
                  </button>
                </div>
              </form>
            )}
          </div>
        </>
      )}
    </div>
  );
}
