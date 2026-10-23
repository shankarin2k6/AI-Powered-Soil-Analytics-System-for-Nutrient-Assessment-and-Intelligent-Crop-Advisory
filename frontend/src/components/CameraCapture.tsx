"use client";

import { useEffect, useRef, useState } from "react";
import Icon from "@/components/Icon";
import { t, useLang } from "@/lib/i18n";

/**
 * Live camera for laptops and desktops (getUserMedia). On phones the app uses the phone's own
 * camera app instead, through <input capture>, which gives better photos on low-end devices.
 * The browser only allows getUserMedia on https:// pages and on localhost.
 */
export default function CameraCapture({ onCapture, onCancel }: { onCapture: (photo: Blob) => void; onCancel: () => void }) {
  useLang();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [ready, setReady] = useState(false);
  const [errorKey, setErrorKey] = useState<string | null>(null);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false })
      .then((s) => {
        if (cancelled) return s.getTracks().forEach((track) => track.stop());
        stream = s;
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch((e: DOMException) => {
        if (cancelled) return;
        setErrorKey(e.name === "NotAllowedError" ? "camera.denied" : e.name === "NotFoundError" ? "camera.none" : "camera.error");
      });

    return () => {
      cancelled = true;
      stream?.getTracks().forEach((track) => track.stop()); // switch the camera light off
    };
  }, []);

  function capture() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")!.drawImage(video, 0, 0);
    canvas.toBlob((blob) => blob && onCapture(blob), "image/jpeg", 0.92);
  }

  return (
    <div className="camera">
      {errorKey ? (
        <p className="error" role="alert">{t(errorKey)}</p>
      ) : (
        <>
          <video ref={videoRef} autoPlay playsInline muted onPlaying={() => setReady(true)} />
          {!ready && <p className="hint">{t("camera.starting")}</p>}
          <button className="big-button primary" disabled={!ready} onClick={capture}>
            <Icon name="camera" /> {t("camera.capture")}
          </button>
        </>
      )}
      <button className="big-button" onClick={onCancel}>{t("camera.cancel")}</button>
    </div>
  );
}
