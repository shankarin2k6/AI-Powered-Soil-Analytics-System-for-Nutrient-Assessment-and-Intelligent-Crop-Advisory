"use client";

import Link from "next/link";
import Icon from "@/components/Icon";
import { ImageRecord, mediaUrl } from "@/lib/api";
import { formatDate, t, useLang } from "@/lib/i18n";

/**
 * Row of small photos, newest first, so the farmer can see (and change) which photo will be analysed.
 * `withLab` holds the ids of photos that have lab values saved with them.
 */
const when = (iso: string) => formatDate(iso);

export default function PhotoPicker({ images, selected, withLab, onSelect }: {
  images: ImageRecord[]; selected: number | null; withLab: Set<number>; onSelect: (id: number) => void;
}) {
  useLang();
  const current = images.find((i) => i.id === selected);
  return (
    <section className="panel picker stack">
      <div className="picker-head">
        <div>
          <h2>{t("analysis.choose.title")}</h2>
          <p className="hint">{t(images.length ? "analysis.choose.hint" : "analysis.choose.empty")}</p>
        </div>
        <Link className="big-button small" href="/capture" aria-label={t("analysis.choose.add_aria")}>
          <Icon name="camera" size={20} /> <span>{t("analysis.choose.add")}</span>
        </Link>
      </div>

      {images.length > 0 && (
        <ul className="thumbs list" role="radiogroup" aria-label={t("analysis.choose.title")}>
          {images.map((img, i) => {
            const on = img.id === selected;
            return (
              <li key={img.id}>
                <button className={`thumb${on ? " on" : ""}`} role="radio" aria-checked={on} onClick={() => onSelect(img.id)}>
                  <span className="thumb-pic">
                    <img src={mediaUrl(img.urls.thumb ?? img.urls.normalized)} alt="" loading="lazy" />
                    {on && <span className="thumb-tick" aria-hidden="true"><Icon name="check" size={16} /></span>}
                    {i === 0 && <span className="thumb-new">{t("analysis.choose.latest")}</span>}
                  </span>
                  <span className="thumb-when">{when(img.created_at)}</span>
                  <span className={`thumb-lab${withLab.has(img.id) ? " yes" : ""}`}>
                    <Icon name="flask" size={14} /> {t(withLab.has(img.id) ? "analysis.choose.with_lab" : "analysis.choose.no_lab")}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {current && !withLab.has(current.id) && (
        <p className="notice">
          <Icon name="alert" size={18} />
          <span>{t("analysis.choose.no_lab_note")} <Link href={`/soil-test?image=${current.id}`}>{t("analysis.add_test")}</Link></span>
        </p>
      )}
    </section>
  );
}
