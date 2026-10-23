"use client";

import { t, useLang } from "@/lib/i18n";

/**
 * The home-page picture: a cross-section of soil with a seedling.
 * On load the layers rise one by one, the roots grow down, then the seedling grows and keeps swaying.
 * All motion is CSS (see "soil profile" in globals.css) and is switched off for people who ask for less motion.
 */
export default function SoilProfile({ className = "" }: { className?: string }) {
  useLang();
  return (
    <svg className={`soil-profile ${className}`} viewBox="0 0 520 540" preserveAspectRatio="xMidYMin slice"
         role="img" aria-label={t("soilprofile.aria")}>
      <defs>
        <clipPath id="sp-slab"><rect x="0" y="150" width="520" height="390" rx="28" /></clipPath>
        <radialGradient id="sp-sun" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor="#f6cf6e" /><stop offset="1" stopColor="#f6cf6e" stopOpacity="0" />
        </radialGradient>
      </defs>

      <circle className="sp-sun-glow" cx="432" cy="84" r="62" fill="url(#sp-sun)" />
      <circle className="sp-sun" cx="432" cy="84" r="28" fill="#f0bf55" />

      <g clipPath="url(#sp-slab)">
        <g className="sp-layer" style={{ ["--i" as string]: 4 }}>
          <path d="M0 190 C90 178 170 200 260 188 S430 176 520 190 V540 H0Z" fill="#2f1f13" />
        </g>
        <g className="sp-layer" style={{ ["--i" as string]: 3 }}>
          <path d="M0 238 C90 250 190 228 270 240 S440 250 520 236 V540 H0Z" fill="#a4472b" />
        </g>
        <g className="sp-layer" style={{ ["--i" as string]: 2 }}>
          <path d="M0 300 C110 290 190 312 280 300 S440 292 520 304 V540 H0Z" fill="#c7954a" />
        </g>
        <g className="sp-layer" style={{ ["--i" as string]: 1 }}>
          <path d="M0 372 C100 384 200 362 290 374 S450 386 520 370 V540 H0Z" fill="#8c7b66" />
        </g>
        <g className="sp-layer" style={{ ["--i" as string]: 0 }}>
          <path d="M0 440 C120 428 200 452 300 440 S450 430 520 442 V540 H0Z" fill="#5d5850" />
          <circle cx="90" cy="490" r="14" fill="#7a746a" /><circle cx="150" cy="512" r="9" fill="#6e6860" />
          <circle cx="330" cy="496" r="16" fill="#7a746a" /><circle cx="420" cy="518" r="10" fill="#6e6860" />
        </g>
        <g className="sp-roots" fill="none" stroke="#e8d3b0" strokeWidth="3" strokeLinecap="round">
          <path pathLength={1} d="M260 190 C258 215 250 235 244 262 S236 300 238 330" />
          <path pathLength={1} d="M259 202 C276 222 290 234 300 260 S312 292 318 312" />
          <path pathLength={1} d="M254 214 C238 228 224 242 214 266" />
          <path pathLength={1} d="M266 226 C282 240 296 244 306 252" />
        </g>

        <g className="sp-labels" fontFamily="Hind, 'Noto Sans Kannada', 'Noto Sans Tamil', system-ui, sans-serif" fontSize="14">
          <text x="26" y="220" fill="#f1e6d8">{t("soilprofile.topsoil")}</text>
          <text x="494" y="220" fill="#f1e6d8" textAnchor="end">0–20 cm</text>
          <text x="26" y="276" fill="#fbe9e0">{t("soilprofile.subsoil")}</text>
          <text x="494" y="276" fill="#fbe9e0" textAnchor="end">20–60 cm</text>
          <text x="26" y="346" fill="#2a1b11">{t("soilprofile.clayloam")}</text>
          <text x="494" y="346" fill="#2a1b11" textAnchor="end">60–100 cm</text>
          <text x="26" y="414" fill="#1e160e">{t("soilprofile.gravel")}</text>
          <text x="494" y="414" fill="#1e160e" textAnchor="end">100–150 cm</text>
        </g>
      </g>

      <g className="sp-sway">
        <g className="sp-grow">
          <path d="M260 190 C260 160 258 130 262 100" fill="none" stroke="#2b7a4b" strokeWidth="5" strokeLinecap="round" />
          <path className="sp-leaf sp-leaf-left" d="M261 128 C236 128 216 114 212 92 C238 90 258 104 261 128Z" fill="#43a06a" />
          <path className="sp-leaf sp-leaf-right" d="M262 108 C288 108 308 92 312 70 C286 70 266 84 262 108Z" fill="#2b7a4b" />
        </g>
      </g>
    </svg>
  );
}
