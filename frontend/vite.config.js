import react from "@vitejs/plugin-react";
// @ts-ignore - types for vite-plugin-pwa are provided at runtime
import { VitePWA } from "vite-plugin-pwa";
import path from "path";
import { fileURLToPath } from "url";
import { defineConfig } from "vite";
// __dirname is not available in ESM by default, emulate it via import.meta.url
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
export default defineConfig({
    plugins: [
        react(),
        VitePWA({
            registerType: "autoUpdate",
            includeAssets: ["favicon.svg", "robots.txt", "apple-touch-icon.png"],
            manifest: {
                name: "Dental Booking — Клиентское приложение",
                short_name: "DentalBooking",
                start_url: "/app",
                scope: "/",
                display: "standalone",
                background_color: "#020617",
                theme_color: "#f8fafc",
            },
            workbox: {
                navigateFallback: "/index.html",
                runtimeCaching: [
                    {
                        urlPattern: /^https?:\/\/.*\/(assets|icons)\//,
                        handler: "StaleWhileRevalidate",
                        options: {
                            cacheName: "static-resources",
                            expiration: {
                                maxEntries: 100,
                                maxAgeSeconds: 7 * 24 * 60 * 60,
                            },
                        },
                    },
                    {
                        urlPattern: /^https?:\/\/.*\/api\/v1\//,
                        handler: "NetworkOnly",
                        options: {
                            cacheName: "api-no-store",
                        },
                    },
                ],
            },
            devOptions: {
                enabled: false,
            },
        }),
    ],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        port: 5175,
        host: true,
        proxy: {
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
                secure: false,
            },
            "/health": {
                target: "http://localhost:8000",
                changeOrigin: true,
                secure: false,
            },
        },
    },
    preview: {
        port: 4173,
        host: true,
    },
});
