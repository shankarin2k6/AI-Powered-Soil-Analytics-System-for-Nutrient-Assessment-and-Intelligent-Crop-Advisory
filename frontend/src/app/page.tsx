"use client";

import Link from "next/link";
import Icon, { IconName } from "@/components/Icon";
import SoilProfile from "@/components/SoilProfile";
import { useAuth } from "@/lib/auth";
import { t, useLang } from "@/lib/i18n";

// The three steps of Milestone 1. Add a step here when a new feature arrives.
const STEPS = [
  { href: "/capture", key: "home.step1" },
  { href: "/soil-test", key: "home.step2" },
  { href: "/history", key: "home.step3" },
];

const TIPS: { icon: IconName; key: string }[] = [
  { icon: "sun", key: "home.tip1" },
  { icon: "frame", key: "home.tip2" },
  { icon: "steady", key: "home.tip3" },
];

export default function Home() {
  useLang();
  const { state } = useAuth();
  const firstName = state.status === "signedIn" ? state.farmer.name.trim().split(/\s+/)[0] : "";

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

      <div className="home-grid">
        <section aria-labelledby="how">
          <h2 id="how" className="section-title">{t("home.steps.title")}</h2>
          <ol className="steps">
            {STEPS.map((s, i) => (
              <li key={s.href} className="step">
                <Link href={s.href} className="step-link">
                  <span className="step-num">{i + 1}</span>
                  <h3>{t(`${s.key}.title`)}</h3>
                  <p>{t(`${s.key}.text`)}</p>
                </Link>
              </li>
            ))}
          </ol>
        </section>

        <aside className="tips" aria-labelledby="tips-title">
          <h2 id="tips-title" className="section-title">{t("home.tips.title")}</h2>
          <ul className="tip-list">
            {TIPS.map((tip) => (
              <li key={tip.key}>
                <span className="tip-icon"><Icon name={tip.icon} /></span>
                <span>{t(tip.key)}</span>
              </li>
            ))}
          </ul>
        </aside>
      </div>

    </>
  );
}
