"use client";

import Link from "next/link";
import { useState } from "react";
import LabValuesDialog from "@/components/LabValuesDialog";
import Icon from "@/components/Icon";
import { ImageRecord, SoilTestRecord, mediaUrl } from "@/lib/api";
import { formatDate, t, useLang } from "@/lib/i18n";

/**
 * Row of small photos, newest first, so the farmer can see (and change) which photo will be analysed.
 * `labByImage` holds the newest lab test saved with each photo; tapping the lab line opens it in a pop-up.
 */
const when = (iso: string) => formatDate(iso);

export default function PhotoPicker({ images, selected, fieldId, labByImage, onSelect, onLabSaved }: {
  images: ImageRecord[]; selected: number | null; fieldId: number | null; labByImage: Map<number, SoilTestRecord>;
  onSelect: (id: number) => void; onLabSaved: (saved: SoilTestRecord) => void;
}) {
  useLang();
  const [open, setOpen] = useState<number | null>(null);          // photo whose lab values are shown in the pop-up
  const openImage = images.find((i) => i.id === open);
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
                </button>
                <button
                  type="button" className={`thumb-lab${labByImage.has(img.id) ? " yes" : ""}`}
                  onClick={() => setOpen(img.id)} aria-label={t("lab.view_aria", { date: when(img.created_at) })}
                >
                  <Icon name="flask" size={14} /> {t(labByImage.has(img.id) ? "analysis.choose.with_lab" : "analysis.choose.no_lab")}
                  <Icon name="edit" size={13} />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {current && !labByImage.has(current.id) && (
        <p className="notice">
          <Icon name="alert" size={18} />
          <span>{t("analysis.choose.no_lab_note")} <Link href={`/soil-test?image=${current.id}`}>{t("analysis.add_test")}</Link></span>
        </p>
      )}
      {openImage && fieldId != null && (
        <LabValuesDialog
          fieldId={fieldId} imageId={openImage.id} imageDate={openImage.created_at} test={labByImage.get(openImage.id) ?? null}
          onClose={() => setOpen(null)} onSaved={(saved) => { onLabSaved(saved); setOpen(null); }}
        />
      )}
    </section>
  );
}
