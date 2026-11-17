import type { Metadata, Viewport } from "next";
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource/hind/400.css";
import "@fontsource/hind/500.css";
import "@fontsource/hind/600.css";
import "@fontsource/hind/700.css";
import "@fontsource/noto-sans-kannada/kannada-400.css";
import "@fontsource/noto-sans-kannada/kannada-500.css";
import "@fontsource/noto-sans-kannada/kannada-600.css";
import "@fontsource/noto-sans-kannada/kannada-700.css";
import "@fontsource/noto-sans-tamil/tamil-400.css";
import "@fontsource/noto-sans-tamil/tamil-500.css";
import "@fontsource/noto-sans-tamil/tamil-600.css";
import "@fontsource/noto-sans-tamil/tamil-700.css";
import AppShell from "@/components/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Soil Analytics",
  description: "Photograph your soil, save lab test values and keep your field records in one place.",
  manifest: "/manifest.json",
  icons: { icon: "/icons/icon-192.png", apple: "/icons/apple-touch-icon.png" },
  appleWebApp: { capable: true, title: "Soil Analytics", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#2b7a4b",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* apply the saved theme and language tag before the first paint (light unless the user chose dark) */}
        <script dangerouslySetInnerHTML={{ __html: "try{var d=document.documentElement;if(localStorage.getItem('theme')==='dark')d.dataset.theme='dark';var l=localStorage.getItem('lang');if(l==='hi'||l==='kn'||l==='ta')d.lang=l}catch(e){}" }} />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
