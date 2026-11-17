/** Small line-icon set (24x24, stroke only). To add an icon, add one entry to PATHS. */

export type IconName =
  | "home" | "camera" | "flask" | "list" | "leaf" | "drop" | "sun" | "check" | "user" | "lock"
  | "mail" | "pin" | "edit" | "chevron" | "close" | "moon" | "chart" | "phone" | "calendar" | "save" | "image" | "alert" | "logout" | "sprout" | "steady" | "frame" | "translate" | "speaker" | "stop";

const PATHS: Record<IconName, string[]> = {
  home: ["M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"],
  camera: ["M4 7h3l2-3h6l2 3h3a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z", "M12 9a4 4 0 1 0 0.01 0z"],
  flask: ["M9 3h6", "M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2.2h12.4a1.5 1.5 0 0 0 1.3-2.2L14 9V3", "M7.5 15h9"],
  list: ["M6 4h12a1 1 0 0 1 1 1v15a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z", "M9 4V3h6v1", "M9 11h6", "M9 15h6"],
  leaf: ["M5 19c0-8 5-14 15-14 0 9-5 15-13 15", "M5 19l8-8"],
  drop: ["M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"],
  sun: ["M12 8a4 4 0 1 0 0.01 0z", "M12 2v2", "M12 20v2", "M2 12h2", "M20 12h2", "M4.9 4.9l1.4 1.4", "M17.7 17.7l1.4 1.4", "M4.9 19.1l1.4-1.4", "M17.7 6.3l1.4-1.4"],
  check: ["M5 12.5l4.5 4.5L19 7.5"],
  user: ["M12 4a4 4 0 1 0 0.01 0z", "M4 21c0-4 4-6 8-6s8 2 8 6"],
  lock: ["M6 11h12a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1z", "M8 11V8a4 4 0 0 1 8 0v3"],
  mail: ["M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z", "M3 7l9 6 9-6"],
  pin: ["M12 21s7-6.2 7-11.5a7 7 0 0 0-14 0C5 14.8 12 21 12 21z", "M12 7.5a2.3 2.3 0 1 0 0.01 0z"],
  edit: ["M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17z", "M14.5 7.5l3 3"],
  chevron: ["M6 9l6 6 6-6"],
  close: ["M6 6l12 12", "M18 6L6 18"],
  moon: ["M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"],
  chart: ["M4 20V11", "M10 20V4", "M16 20v-6", "M22 20H2"],
  phone: ["M8 2h8a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z", "M11 18h2"],
  calendar: ["M4 5h16a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z", "M3 10h18", "M8 3v4", "M16 3v4"],
  save: ["M5 3h11l3 3v15H5z", "M8 3v6h8V3", "M8 21v-7h8v7"],
  image: ["M4 4h16a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z", "M9 8.5a1.5 1.5 0 1 0 0.01 0z", "M21 16l-5-5-8 9"],
  alert: ["M12 3l10 18H2z", "M12 10v5", "M12 18h.01"],
  logout: ["M9 21H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h4", "M16 17l5-5-5-5", "M21 12H9"],
  sprout: ["M12 21v-9", "M12 12c0-4-3-6-7-6 0 4 3 6 7 6z", "M12 14c0-3 2-5 6-5 0 3-2 5-6 5z"],
  steady: ["M12 3v4", "M8 7h8", "M7 21h10", "M12 7v14", "M9 12l3-2 3 2"],
  translate: ["M3 5h10", "M8 3v2", "M5 5c.6 3.6 3 6.4 7 8.2", "M11.5 5c-.7 3.8-3.4 6.8-7.5 8.6", "M12.5 21l4-9.5 4 9.5", "M13.9 18h5.2"],
  speaker: ["M4 9v6h4l5 4V5L8 9z", "M16.5 8.5a5 5 0 0 1 0 7", "M19 6a8.5 8.5 0 0 1 0 12"],
  stop: ["M7 7h10v10H7z"],
  frame: ["M4 8V5a1 1 0 0 1 1-1h3", "M16 4h3a1 1 0 0 1 1 1v3", "M20 16v3a1 1 0 0 1-1 1h-3", "M8 20H5a1 1 0 0 1-1-1v-3"],
};

export default function Icon({ name, size = 22 }: { name: IconName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {PATHS[name].map((d) => <path key={d} d={d} pathLength={1} />)}
    </svg>
  );
}
