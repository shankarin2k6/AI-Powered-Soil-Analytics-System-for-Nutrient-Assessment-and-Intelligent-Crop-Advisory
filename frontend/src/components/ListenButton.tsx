"use client";

import { useEffect, useRef, useState } from "react";
import Icon from "@/components/Icon";
import { ApiError, AnalysisRecord, api } from "@/lib/api";
import { getLanguage, t, useLang } from "@/lib/i18n";
import { spokenSummary } from "@/lib/spoken";

/** "Listen" button: reads the result aloud in the chosen language. Hidden when the server has no Sarvam key. */
export default function ListenButton({ record }: { record: AnalysisRecord }) {
  useLang();
  const [enabled, setEnabled] = useState(false);
  const [state, setState] = useState<"idle" | "loading" | "playing">("idle");
  const [error, setError] = useState<string | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const url = useRef<{ key: string; src: string } | null>(null);    // the last audio, so a replay is instant

  useEffect(() => {
    api.voiceStatus().then((s) => setEnabled(s.enabled)).catch(() => setEnabled(false));
    return () => { audio.current?.pause(); if (url.current) URL.revokeObjectURL(url.current.src); };
  }, []);

  // changing the language while listening stops the old voice
  const lang = getLanguage();
  useEffect(() => { audio.current?.pause(); setState("idle"); setError(null); }, [lang]);

  if (!enabled) return null;

  async function toggle() {
    if (state === "playing") { audio.current?.pause(); setState("idle"); return; }
    if (state === "loading") return;
    setError(null);
    const language = getLanguage();
    const text = spokenSummary(record);
    const key = `${language}|${text}`;
    try {
      if (url.current?.key !== key) {
        setState("loading");
        const blob = await api.speak(text, language);
        if (url.current) URL.revokeObjectURL(url.current.src);
        url.current = { key, src: URL.createObjectURL(blob) };
      }
      const el = new Audio(url.current.src);
      audio.current = el;
      el.onended = () => setState("idle");
      el.onerror = () => { setState("idle"); setError("voice.error"); };
      await el.play();
      setState("playing");
    } catch (e) {
      setState("idle");
      setError(e instanceof ApiError && e.messageKey ? e.messageKey : "voice.error");
    }
  }

  return (
    <div className="listen no-print">
      <button type="button" className={`big-button${state === "playing" ? "" : " primary"}`} onClick={toggle}
              disabled={state === "loading"} aria-pressed={state === "playing"}>
        <Icon name={state === "playing" ? "stop" : "speaker"} />
        {state === "loading" ? t("voice.loading") : state === "playing" ? t("voice.stop") : t("voice.listen")}
      </button>
      {error && <p className="notice" role="alert"><Icon name="alert" size={18} /> {t(error)}</p>}
    </div>
  );
}
