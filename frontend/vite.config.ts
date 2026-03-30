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
      includeAssets: [
        "pwa-icon.svg",
        "pwa-icon-192.png",
        "pwa-icon-512.png",
        "pwa-icon-512-maskable.png",
        "apple-touch-icon.png",
        "screenshots/pwa-booking.png",
        "screenshots/pwa-chat.png",
        "emoji-datasource/apple/sheets-256/64.png",
      ],
      manifest: {
        id: "/",
        name: "Dental Booking — приложение пациента",
        short_name: "DentalBooking",
        description:
          "Запись к врачу, чат с клиникой, профиль и уведомления — PWA для пациентов стоматологии.",
        lang: "ru",
        start_url: "/app",
        scope: "/",
        display: "standalone",
        display_override: ["standalone", "minimal-ui"],
        orientation: "portrait-primary",
        background_color: "#F4F6F8",
        theme_color: "#1C2E45",
        categories: ["health", "medical", "lifestyle"],
        icons: [
          {
            src: "/pwa-icon-192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any",
          },
          {
            src: "/pwa-icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any",
          },
          {
            src: "/pwa-icon-512-maskable.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
          {
            src: "/pwa-icon.svg",
            sizes: "512x512",
            type: "image/svg+xml",
            purpose: "any",
          },
        ],
        screenshots: [
          {
            src: "/screenshots/pwa-booking.png",
            sizes: "1080x1920",
            type: "image/png",
            form_factor: "narrow",
            label: "Booking flow",
          },
          {
            src: "/screenshots/pwa-chat.png",
            sizes: "1080x1920",
            type: "image/png",
            form_factor: "narrow",
            label: "Clinic chat",
          },
        ],
        shortcuts: [
          {
            name: "Запись",
            short_name: "Запись",
            description: "Открыть запись к врачу",
            url: "/app/booking",
          },
          {
            name: "Чат",
            short_name: "Чат",
            description: "Сообщения с клиникой",
            url: "/app/chat",
          },
        ],
      },
      workbox: {
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/\/api\//, /\/health(?:\/|$)/],
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
