/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The service worker file must never be kept by the browser's HTTP cache, or phones keep running an old one.
  async headers() {
    return [
      { source: "/sw.js", headers: [{ key: "Cache-Control", value: "no-cache, no-store, must-revalidate" }, { key: "Service-Worker-Allowed", value: "/" }] },
      { source: "/manifest.json", headers: [{ key: "Cache-Control", value: "no-cache" }] },
    ];
  },
  // Testing on a real phone over your Wi-Fi: add your computer's address, e.g. allowedDevOrigins: ["192.168.1.5"],
  // Milestone 3: wrap this config with the PWA plugin (service worker) and add the i18n settings here.
};

export default nextConfig;
