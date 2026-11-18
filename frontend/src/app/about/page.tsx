"use client";

import { useEffect, useRef, useState } from "react";
import Icon, { IconName } from "@/components/Icon";
import PageHead from "@/components/PageHead";
import { t, useLang } from "@/lib/i18n";

/** Adds the class "in" to an element the first time it scrolls into view, so its CSS animation can play. */
function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") { setSeen(true); return; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold: 0.2 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return [ref, seen] as const;
}

/** A number that counts up from 0 when it comes into view. */
function Counter({ to }: { to: number }) {
  const [ref, seen] = useReveal<HTMLSpanElement>();
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!seen) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setN(to); return; }
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const k = Math.min(1, (now - start) / 1400);
      setN(Math.round(to * (1 - Math.pow(1 - k, 3))));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [seen, to]);
  return <span ref={ref}>{n}</span>;
}

function Reveal({ children, className = "", delay = 0, as: Tag = "div" }: {
  children: React.ReactNode; className?: string; delay?: number; as?: "div" | "li" | "section";
}) {
  const [ref, seen] = useReveal<HTMLElement>();
  return (
    <Tag ref={ref as never} className={`reveal ${seen ? "in" : ""} ${className}`} style={{ ["--d" as string]: `${delay}ms` }}>
      {children}
    </Tag>
  );
}

const STACK: { title: string; icon: IconName; items: string[] }[] = [
  { title: "about.stack.frontend", icon: "phone", items: ["Next.js 16", "React 19", "TypeScript", "Plain CSS", "PWA"] },
  { title: "about.stack.backend", icon: "list", items: ["FastAPI", "SQLAlchemy 2", "Alembic", "PostgreSQL 16", "argon2 + JWT"] },
  { title: "about.stack.ai", icon: "chart", items: ["PyTorch (training)", "EfficientNet-B0", "ONNX Runtime", "XGBoost", "OpenCV", "Grad-CAM", "SHAP"] },
  { title: "about.stack.voice", icon: "speaker", items: ["Sarvam AI", "Service worker", "Web app manifest"] },
  { title: "about.stack.deploy", icon: "leaf", items: ["Docker", "Caddy HTTPS", "Free-tier hosting", "S3 / Cloud Storage"] },
];

const STEPS: { key: string; icon: IconName; state: "done" | "next" }[] = [
  { key: "m1", icon: "camera", state: "done" },
  { key: "m2", icon: "flask", state: "done" },
  { key: "m3", icon: "sprout", state: "done" },
  { key: "next", icon: "pin", state: "next" },
];

const STATS: { to: number; label: string }[] = [
  { to: 3, label: "about.stat.milestones" },
  { to: 4, label: "about.stat.languages" },
  { to: 20, label: "about.stat.crops" },
  { to: 213, label: "about.stat.tests" },
];

export default function AboutPage() {
  useLang();
  return (
    <div className="about">
      <PageHead title={t("about.title")} lead={t("about.lead")} />

      {/* hero: a sprout draws itself and soil specks drift up */}
      <section className="about-hero" aria-label={t("about.tagline")}>
        <div className="about-specks" aria-hidden="true">
          {Array.from({ length: 14 }, (_, i) => <i key={i} style={{ ["--x" as string]: `${(i * 37) % 100}%`, ["--t" as string]: `${7 + (i % 5) * 2}s`, ["--w" as string]: `${-i * 1.3}s` }} />)}
        </div>
        <svg className="about-sprout" viewBox="0 0 120 140" aria-hidden="true">
          <ellipse cx="60" cy="128" rx="38" ry="8" className="soil" />
          <path className="stem" d="M60 126 C58 98 62 76 60 52" />
          <path className="leaf l1" d="M60 84 C26 84 12 62 12 40 C42 40 58 58 60 84 Z" />
          <path className="leaf l2" d="M60 64 C92 64 108 42 108 18 C78 18 62 38 60 64 Z" />
        </svg>
        <div className="about-hero-text">
          <p className="about-kicker">Soil Analytics</p>
          <h2>{t("about.tagline")}</h2>
          <p>{t("about.what.text")}</p>
        </div>
      </section>

      <ul className="about-stats list">
        {STATS.map((s, i) => (
          <Reveal as="li" key={s.label} className="about-stat" delay={i * 90}>
            <strong><Counter to={s.to} />{s.to >= 200 ? "+" : ""}</strong>
            <span>{t(s.label)}</span>
          </Reveal>
        ))}
      </ul>

      <section className="about-section">
        <Reveal><h2><Icon name="leaf" size={24} /> {t("about.stack.title")}</h2></Reveal>
        <div className="about-stack">
          {STACK.map((g, gi) => (
            <Reveal key={g.title} className="about-group" delay={gi * 80}>
              <h3><Icon name={g.icon} size={20} /> {t(g.title)}</h3>
              <ul className="list about-chips">
                {g.items.map((it, i) => <li key={it} style={{ ["--c" as string]: i }}>{it}</li>)}
              </ul>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="about-section">
        <Reveal><h2><Icon name="sprout" size={24} /> {t("about.journey.title")}</h2></Reveal>
        <ol className="about-timeline list">
          {STEPS.map((s, i) => (
            <Reveal as="li" key={s.key} className={`about-step ${s.state}`} delay={i * 110}>
              <span className="about-dot"><Icon name={s.icon} size={20} /></span>
              <div>
                <h3>{t(`about.step.${s.key}.title`)}</h3>
                <p>{t(`about.step.${s.key}.text`)}</p>
              </div>
            </Reveal>
          ))}
        </ol>
      </section>

      <section className="about-section">
        <Reveal><h2><Icon name="user" size={24} /> {t("about.dev.title")}</h2></Reveal>
        <Reveal className="about-dev">
          <div className="about-avatar" aria-hidden="true"><span>S</span></div>
          <div>
            <h3>Shankari N</h3>
            <p className="about-role">{t("about.dev.role")}</p>
            <p>{t("about.dev.text")}</p>
            <p className="about-program"><Icon name="pin" size={18} /> {t("about.program")}</p>
          </div>
        </Reveal>
      </section>

      <Reveal className="about-note">
        <Icon name="alert" size={20} /> <span>{t("about.note")}</span>
      </Reveal>
      <p className="about-foot">{t("about.foot")}</p>
    </div>
  );
}
