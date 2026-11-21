"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Icon, { IconName } from "@/components/Icon";
import Reveal from "@/components/Reveal";
import SoilProfile from "@/components/SoilProfile";
import { useAuth } from "@/lib/auth";
import { t, useLang } from "@/lib/i18n";

// The three steps. Each one is a section of the page with a button that goes to its page.
const STEPS: { n: 1 | 2 | 3; href: string; key: string; cta: string; icon: IconName }[] = [
  { n: 1, href: "/capture", key: "home.step1", cta: "home.cta.photo", icon: "camera" },
  { n: 2, href: "/soil-test", key: "home.step2", cta: "home.cta.test", icon: "flask" },
  { n: 3, href: "/history", key: "home.step3", cta: "home.step3.go", icon: "list" },
];

const TIPS: { icon: IconName; key: string }[] = [
  { icon: "sun", key: "home.tip1" },
  { icon: "frame", key: "home.tip2" },
  { icon: "steady", key: "home.tip3" },
];

// What the app gives you. Each card opens the page where the feature lives.
const FEATURES: { icon: IconName; key: string; href: string }[] = [
  { icon: "chart", key: "home.f1", href: "/analysis" },
  { icon: "sprout", key: "home.f2", href: "/analysis" },
  { icon: "drop", key: "home.f3", href: "/analysis" },
  { icon: "steady", key: "home.f4", href: "/history" },
  { icon: "phone", key: "home.f5", href: "/about" },
  { icon: "translate", key: "home.f6", href: "/about" },
];

/** Small pictures that show what each step looks like. They are examples, not the farmer's data. */
function PhotoMock() {
  return (
    <div className="hs-mock hs-photo" aria-hidden="true">
      <div className="hs-phone">
        <div className="hs-soil" />
        <span className="hs-corner tl" /><span className="hs-corner tr" /><span className="hs-corner bl" /><span className="hs-corner br" />
        <span className="hs-scan" />
      </div>
      <ul className="hs-chips">
        <li style={{ ["--c" as string]: 0 }}><Icon name="sun" /> {t("home.mock.light")}</li>
        <li style={{ ["--c" as string]: 1 }}><Icon name="check" /> {t("home.mock.sharp")}</li>
        <li style={{ ["--c" as string]: 2 }}><Icon name="frame" /> {t("home.mock.frame")}</li>
      </ul>
    </div>
  );
}

function FormMock() {
  const rows: [string, number, string][] = [["N", 78, "78"], ["P", 46, "46"], ["K", 64, "64"], ["pH", 62, "6.5"]];
  return (
    <div className="hs-mock hs-form" aria-hidden="true">
      <span className="hs-tag">{t("home.mock.example")}</span>
      {rows.map(([label, pct, value], i) => (
        <div key={label} className="hs-row" style={{ ["--i" as string]: i }}>
          <span className="hs-row-label">{label}</span>
          <span className="hs-track"><span className="hs-fill" style={{ ["--w" as string]: `${pct}%` }} /></span>
          <span className="hs-row-value">{value}</span>
        </div>
      ))}
    </div>
  );
}

function ScoreMock() {
  const C = 2 * Math.PI * 54;
  return (
    <div className="hs-mock hs-score" aria-hidden="true">
      <span className="hs-tag">{t("home.mock.example")}</span>
      <svg viewBox="0 0 140 140" className="hs-ring">
        <circle cx="70" cy="70" r="54" className="hs-ring-bg" />
        <circle cx="70" cy="70" r="54" className="hs-ring-fill" style={{ ["--len" as string]: C, ["--to" as string]: C * (1 - 0.72) }} transform="rotate(-90 70 70)" />
        <text x="70" y="68" textAnchor="middle" className="hs-ring-num">72</text>
        <text x="70" y="88" textAnchor="middle" className="hs-ring-sub">/ 100</text>
      </svg>
      <p className="hs-score-label">{t("home.mock.score")}</p>
      <span className="hs-saved"><Icon name="save" /> {t("home.mock.saved")}</span>
    </div>
  );
}

const MOCKS = { 1: PhotoMock, 2: FormMock, 3: ScoreMock };

export default function Home() {
  useLang();
  const { state } = useAuth();
  const firstName = state.status === "signedIn" ? state.farmer.name.trim().split(/\s+/)[0] : "";
  const [active, setActive] = useState<number>(1);

  // Highlight the step whose card is closest to the middle of the screen.
  useEffect(() => {
    let raf = 0;
    const update = () => {
      raf = 0;
      const mid = window.innerHeight / 2;
      let best = 1, bestDist = Infinity;
      document.querySelectorAll<HTMLElement>("[data-step]").forEach((el) => {
        const r = el.getBoundingClientRect();
        const d = Math.abs(r.top + r.height / 2 - mid);
        if (d < bestDist) { bestDist = d; best = Number(el.dataset.step); }
      });
      setActive(best);
    };
    const onScroll = () => { if (!raf) raf = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => { window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); if (raf) cancelAnimationFrame(raf); };
  }, []);

  const goTo = (n: number) => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.getElementById(`step-${n}`)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
  };

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="hero-greeting">{firstName ? t("home.greeting", { name: firstName }) : t("home.greeting.plain")}</p>
          <h1 className="hero-title">{t("home.title")}</h1>
          <p className="hero-lead">{t("home.lead")}</p>
          <div className="hero-actions">
            <Link className="big-button primary" href="/capture"><Icon name="camera" /> {t("home.cta.photo")}</Link>
            <Link className="big-button ghost" href="/soil-test"><Icon name="flask" /> {t("home.cta.test")}</Link>
          </div>
        </div>
        <div className="hero-art"><SoilProfile /></div>
      </section>

      <section className="hs" aria-labelledby="how">
        <div className="hs-head">
          <h2 id="how" className="section-title">{t("home.steps.title")}</h2>
          <p className="hs-lead">{t("home.steps.lead")}</p>
        </div>

        <nav className="hs-rail" aria-label={t("home.rail.aria")}>
          {STEPS.map((s) => (
            <button key={s.n} type="button" className={`hs-rail-btn ${active === s.n ? "on" : ""}`} aria-current={active === s.n ? "step" : undefined} onClick={() => goTo(s.n)}>
              <span className="hs-rail-num">{s.n}</span>
              <span className="hs-rail-text">{t(`${s.key}.title`)}</span>
            </button>
          ))}
        </nav>

        {STEPS.map((s) => {
          const Mock = MOCKS[s.n];
          return (
            <section key={s.n} id={`step-${s.n}`} data-step={s.n} className="hs-step" aria-labelledby={`step-${s.n}-title`}>
              <Reveal className={`hs-card ${s.n % 2 === 0 ? "flip" : ""}`}>
                <div className="hs-art"><Mock /></div>
                <div className="hs-copy">
                  <span className="hs-badge"><Icon name={s.icon} /> {t("home.step.of", { n: s.n })}</span>
                  <h3 id={`step-${s.n}-title`}>{t(`${s.key}.title`)}</h3>
                  <p>{t(`${s.key}.text`)}</p>
                  <ul className="hs-points">
                    {[1, 2, 3].map((k) => (
                      <li key={k}><span className="hs-tick"><Icon name="check" /></span>{t(`${s.key}.p${k}`)}</li>
                    ))}
                  </ul>
                  <Link className="big-button primary hs-go" href={s.href}><Icon name={s.icon} /> {t(s.cta)}</Link>
                </div>
              </Reveal>
            </section>
          );
        })}
      </section>

      <section className="hs" aria-labelledby="tips-title">
        <div className="hs-head">
          <h2 id="tips-title" className="section-title">{t("home.tips.title")}</h2>
        </div>
        <ul className="hs-tips">
          {TIPS.map((tip, i) => (
            <li key={tip.key}>
              <Reveal className="hs-tip" delay={i * 90}>
                <span className="hs-tip-icon"><Icon name={tip.icon} /></span>
                <span>{t(tip.key)}</span>
              </Reveal>
            </li>
          ))}
        </ul>
      </section>

      <section className="hs" aria-labelledby="features-title">
        <div className="hs-head">
          <h2 id="features-title" className="section-title">{t("home.features.title")}</h2>
          <p className="hs-lead">{t("home.features.lead")}</p>
        </div>
        <ul className="hs-features">
          {FEATURES.map((f, i) => (
            <li key={f.key}>
              <Reveal delay={(i % 3) * 90}>
                <Link href={f.href} className="hs-feature">
                  <span className="hs-feature-icon"><Icon name={f.icon} /></span>
                  <h3>{t(`${f.key}.title`)}</h3>
                  <p>{t(`${f.key}.text`)}</p>
                  <span className="hs-feature-go" aria-hidden="true"><Icon name="chevron" /></span>
                </Link>
              </Reveal>
            </li>
          ))}
        </ul>
      </section>

      <Reveal className="hs-cta">
        <h2>{t("home.cta2.title")}</h2>
        <p>{t("home.cta2.text")}</p>
        <div className="hs-cta-actions">
          <Link className="big-button primary" href="/capture"><Icon name="camera" /> {t("home.cta.photo")}</Link>
          <Link className="big-button ghost" href="/soil-test"><Icon name="flask" /> {t("home.cta.test")}</Link>
        </div>
      </Reveal>
    </>
  );
}
