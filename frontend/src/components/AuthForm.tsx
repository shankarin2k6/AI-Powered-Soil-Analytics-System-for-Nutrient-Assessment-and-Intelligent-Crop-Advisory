"use client";

import Icon from "@/components/Icon";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { normalizePhone } from "@/lib/phone";
import { t, useLang } from "@/lib/i18n";

/** One form for both pages: mode "signup" also asks for a name. */
export default function AuthForm({ mode }: { mode: "login" | "signup" }) {
  useLang();
  const { login, signup } = useAuth();
  const isSignup = mode === "signup";

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);

    const found: Record<string, string> = {};
    const cleanPhone = normalizePhone(phone);
    if (isSignup && !name.trim()) found.name = t("auth.error.name");
    if (!cleanPhone) found.phone = t("auth.error.phone");
    if (!password) found.password = t("auth.error.password_required");
    else if (isSignup && password.length < 8) found.password = t("auth.error.password");
    setErrors(found);
    if (Object.keys(found).length || !cleanPhone) return;

    setBusy(true);
    try {
      // on success the AuthProvider switches to "signed in" and the app moves to the home page
      if (isSignup) await signup(name.trim(), cleanPhone, password);
      else await login(cleanPhone, password);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setFormError(t("auth.error.wrong_credentials"));
      else if (err instanceof ApiError && err.status === 409) setFormError(t("auth.error.phone_taken"));
      else setFormError(t(err instanceof ApiError && err.messageKey ? err.messageKey : "error.generic"));
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={onSubmit} noValidate>
      <div className="page-head">
        <h1>{t(isSignup ? "auth.signup.title" : "auth.login.title")}</h1>
        <p className="lead">{t(isSignup ? "auth.signup.lead" : "auth.login.lead")}</p>
      </div>

      {isSignup && (
        <label className="field">
          <span className="label"><Icon name="user" size={18} /> {t("auth.name")}</span>
          <input type="text" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)}
                 aria-invalid={!!errors.name} />
          {errors.name && <span className="error" role="alert">{errors.name}</span>}
        </label>
      )}

      <label className="field">
        <span className="label"><Icon name="phone" size={18} /> {t("auth.phone")}</span>
        <input type="tel" inputMode="tel" autoComplete="tel" placeholder="98765 43210" value={phone}
               onChange={(e) => setPhone(e.target.value)} aria-invalid={!!errors.phone} />
        {errors.phone && <span className="error" role="alert">{errors.phone}</span>}
      </label>

      <label className="field">
        <span className="label"><Icon name="lock" size={18} /> {t("auth.password")}</span>
        <span className="input-row">
          <input type={showPassword ? "text" : "password"} autoComplete={isSignup ? "new-password" : "current-password"}
                 value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={!!errors.password} />
          <button type="button" className="link-button" onClick={() => setShowPassword(!showPassword)}>
            {t(showPassword ? "auth.hide" : "auth.show")}
          </button>
        </span>
        {isSignup && <small className="hint">{t("auth.password.hint")}</small>}
        {errors.password && <span className="error" role="alert">{errors.password}</span>}
      </label>

      {formError && <p className="error" role="alert">{formError}</p>}
      <button className="big-button primary" type="submit" disabled={busy}>
        {busy ? t("auth.wait") : t(isSignup ? "auth.signup" : "auth.login")}
      </button>
      <Link className="text-link" href={isSignup ? "/login" : "/signup"}>
        {t(isSignup ? "auth.to_login" : "auth.to_signup")}
      </Link>
    </form>
  );
}
