"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Icon from "@/components/Icon";
import CameraCapture from "@/components/CameraCapture";
import { ApiError, ImageRecord, api, mediaUrl } from "@/lib/api";
import { prepareForUpload } from "@/lib/image";
import { ensureField } from "@/lib/session";
import { t, useLang } from "@/lib/i18n";

type Step =
  | { name: "idle" }
  | { name: "preparing" }
  | { name: "preview"; blob: Blob; previewUrl: string }
  | { name: "uploading"; previewUrl: string }
  | { name: "saved"; image: ImageRecord };

export default function PhotoCapture() {
  useLang();
  const [step, setStep] = useState<Step>({ name: "idle" });
  const [error, setError] = useState<string | null>(null);
  const [liveCamera, setLiveCamera] = useState(false);       // the webcam view is open
  const [canUseLive, setCanUseLive] = useState(false);       // this device should use the webcam view

  // Laptops and desktops: browsers ignore <input capture> there and open a file picker, so use the
  // webcam instead. Phones and tablets (coarse pointer) keep the native camera app.
  useEffect(() => {
    setCanUseLive(
      window.isSecureContext && !!navigator.mediaDevices?.getUserMedia && !window.matchMedia("(pointer: coarse)").matches,
    );
  }, []);

  // free the preview picture from memory when it is replaced
  useEffect(() => {
    return () => {
      if (step.name === "preview" || step.name === "uploading") URL.revokeObjectURL(step.previewUrl);
    };
  }, [step]);

  async function onPick(file: Blob | undefined) {
    if (!file) return;
    setError(null);
    setStep({ name: "preparing" });
    const blob = await prepareForUpload(file);
    setStep({ name: "preview", blob, previewUrl: URL.createObjectURL(blob) });
  }

  async function onUpload() {
    if (step.name !== "preview") return;
    const { blob, previewUrl } = step;
    setStep({ name: "uploading", previewUrl });
    try {
      const fieldId = await ensureField();
      const image = await api.uploadImage(fieldId, blob);
      setStep({ name: "saved", image });
    } catch (e) {
      setError(t(e instanceof ApiError && e.messageKey ? e.messageKey : "error.generic"));
      setStep({ name: "preview", blob, previewUrl });
    }
  }

  if (step.name === "saved") {
    const { image } = step;
    return (
      <div className="stack">
        <p className="success"><span className="check-badge"><Icon name="check" size={18} /></span>{t("capture.saved")}</p>
        <img className="photo" src={mediaUrl(image.urls.normalized)} alt="" />
        {image.quality.warnings.map((w) => (
          <p key={w} className="notice"><Icon name="alert" size={18} /> {t(w)}</p>
        ))}
        <Link className="big-button primary" href={`/soil-test?image=${image.id}`}>
          <Icon name="flask" /> {t("capture.next")}
        </Link>
        <button className="big-button" onClick={() => { setStep({ name: "idle" }); if (canUseLive) setLiveCamera(true); }}>
          <Icon name="camera" /> {t("capture.retake")}
        </button>
      </div>
    );
  }

  if (liveCamera) {
    return (
      <CameraCapture
        onCapture={(photo) => { setLiveCamera(false); onPick(photo); }}
        onCancel={() => setLiveCamera(false)}
      />
    );
  }

  const previewUrl = step.name === "preview" || step.name === "uploading" ? step.previewUrl : null;
  const busy = step.name === "preparing" || step.name === "uploading";

  return (
    <div className="stack">
      <p className="hint">{t("capture.tip")}</p>

      {previewUrl && <img className="photo" src={previewUrl} alt="" />}
      {step.name === "preparing" && <p className="hint">{t("capture.checking")}</p>}
      {error && <p className="error" role="alert">{error}</p>}

      {step.name === "preview" || step.name === "uploading" ? (
        <button className="big-button primary" disabled={busy} onClick={onUpload}>
          <Icon name="save" /> {step.name === "uploading" ? t("capture.uploading") : t("capture.upload")}
        </button>
      ) : null}

      {canUseLive ? (
        <button className={`big-button ${previewUrl ? "" : "primary"}`} disabled={busy} onClick={() => setLiveCamera(true)}>
          <Icon name="camera" /> {previewUrl ? t("capture.retake") : t("capture.camera")}
        </button>
      ) : (
        /* capture="environment" opens the back camera app directly on Android; no file picker is shown */
        <label className={`big-button ${previewUrl ? "" : "primary"}`}>
          <Icon name="camera" /> {previewUrl ? t("capture.retake") : t("capture.camera")}
          <input type="file" accept="image/*" capture="environment" hidden disabled={busy}
                 onChange={(e) => { onPick(e.target.files?.[0]); e.target.value = ""; }} />
        </label>
      )}
      <label className="big-button">
        <Icon name="image" /> {t("capture.gallery")}
        <input type="file" accept="image/jpeg,image/png" hidden disabled={busy}
               onChange={(e) => { onPick(e.target.files?.[0]); e.target.value = ""; }} />
      </label>
    </div>
  );
}
