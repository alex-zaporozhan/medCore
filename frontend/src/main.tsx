import "@mantine/core/styles.css";
import "@mantine/spotlight/styles.css";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import "@fontsource/inter/cyrillic-400.css";
import "@fontsource/inter/cyrillic-500.css";
import "@fontsource/inter/cyrillic-600.css";
import "@fontsource/inter/cyrillic-700.css";
import "@fontsource/inter/cyrillic-ext-400.css";
import "@fontsource/inter/cyrillic-ext-500.css";
import "@fontsource/inter/cyrillic-ext-600.css";
import "@fontsource/inter/cyrillic-ext-700.css";
import "./index.css";

import { ColorSchemeScript, MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { appTheme } from "./theme";
import { registerPwa } from "./pwa/registerPwa";

/** Вход: стили Mantine → `MantineProvider` → `QueryClientProvider` → `App`. §7: смена UI-kit — только по эпику (`ROLE_FRONTEND`). Базовые дефолты Query: `docs/artifacts/ARCH_FRONTEND_ENTERPRISE_BASELINE.md`. */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ColorSchemeScript defaultColorScheme="light" />
    <MantineProvider theme={appTheme} defaultColorScheme="light">
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>
);

registerPwa();
