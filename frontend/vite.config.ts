import react from "@vitejs/plugin-react";
// @ts-ignore - types for vite-plugin-pwa are provided at runtime
import { VitePWA } from "vite-plugin-pwa";
import http from "node:http";
import net from "node:net";
import path from "path";
import { fileURLToPath } from "url";
import { defineConfig, type Plugin } from "vite";

// __dirname is not available in ESM by default, emulate it via import.meta.url
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** Host uvicorn publishes :8000; docker compose publishes API as :8010. */
const API_PROXY_CANDIDATES: ReadonlyArray<{ origin: string; port: number }> = [
  { origin: "http://127.0.0.1:8000", port: 8000 },
  { origin: "http://127.0.0.1:8010", port: 8010 },
];

/**
 * Vite uses node-http-proxy, not http-proxy-middleware. A `router` callback is ignored.
 * Mutate this object in place: each proxied request shallow-copies `target` from here.
 */
const apiProxy = {
  target: "http://127.0.0.1:8010",
  changeOrigin: true,
  secure: false,
};

function portOpen(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = net.connect({ host: "127.0.0.1", port, timeout: 800 }, () => {
      socket.end();
      resolve(true);
    });
    socket.on("error", () => resolve(false));
    socket.on("timeout", () => {
      socket.destroy();
      resolve(false);
    });
  });
}

function originHealthOk(origin: string): Promise<boolean> {
  return new Promise((resolve) => {
    const url = new URL("/health", origin);
    const req = http.get(
      {
        hostname: url.hostname,
        port: url.port,
        path: url.pathname,
        timeout: 800,
      },
      (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      },
    );
    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function resolveApiProxyTarget(): Promise<string> {
  const override = (process.env.VITE_API_PROXY_TARGET || "").trim().replace(/\/$/, "");
  if (override) return override;
  for (const candidate of API_PROXY_CANDIDATES) {
    if (await originHealthOk(candidate.origin)) return candidate.origin;
  }
  for (const candidate of API_PROXY_CANDIDATES) {
    if (await portOpen(candidate.port)) return candidate.origin;
  }
  return "http://127.0.0.1:8010";
}

async function refreshLiveProxyTarget(): Promise<string> {
  const next = await resolveApiProxyTarget();
  if (apiProxy.target !== next) {
    apiProxy.target = next;
    console.info(`[vite] /api proxy → ${next}`);
  }
  return next;
}

function liveApiProxyPlugin(): Plugin {
  let pollStarted = false;
  const startPoll = () => {
    if (pollStarted) return;
    if ((process.env.VITE_API_PROXY_TARGET || "").trim()) return;
    pollStarted = true;
    const timer = setInterval(() => {
      void refreshLiveProxyTarget();
    }, 4000);
    timer.unref?.();
  };
  return {
    name: "live-api-proxy-target",
    configureServer() {
      startPoll();
    },
    configurePreviewServer() {
      startPoll();
    },
  };
}

export default defineConfig(async () => {
  await refreshLiveProxyTarget();
  console.info(`[vite] /api proxy → ${apiProxy.target}`);
  return {
  plugins: [
    liveApiProxyPlugin(),
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
        name: "Единая система управления — приложение клиента",
        short_name: "ЕСУ",
        description:
          "Запись, чат с организацией, профиль и уведомления — PWA для клиентов сервисных компаний.",
        lang: "ru",
        start_url: "/app",
        scope: "/",
        display: "standalone",
        display_override: ["standalone", "minimal-ui"],
        orientation: "portrait-primary",
        background_color: "#F4F6F8",
        theme_color: "#1e40af",
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
        /** Main SPA chunk is ~2.35 MiB with i18n dictionaries; keep SW precache above that. */
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024,
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/\/api\//, /\/health(?:\/|$)/],
        runtimeCaching: [
          // Hashed JS chunks must not be served stale after a deploy: an old index-*.js can
          // reference EmojiMartApplePickerPane-<oldhash>.js that no longer exists → dynamic import fails.
          {
            urlPattern: ({ url }) =>
              url.pathname.startsWith("/assets/") && url.pathname.endsWith(".js"),
            handler: "NetworkFirst",
            options: {
              cacheName: "assets-js-network-first",
              networkTimeoutSeconds: 5,
              expiration: {
                maxEntries: 80,
                maxAgeSeconds: 24 * 60 * 60,
              },
            },
          },
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
      // Pass the same object (do not spread): Vite/http-proxy reads `target` per request.
      "/api": apiProxy,
      "/health": apiProxy,
    },
  },
  preview: {
    port: 4173,
    host: true,
    // Same as dev: без прокси запросы идут на 4173 и /api не доходит до API — форма входа «молчит» или 404.
    proxy: {
      "/api": apiProxy,
      "/health": apiProxy,
    },
  },
};
});
