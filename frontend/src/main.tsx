import "@mantine/core/styles.css";
import "@mantine/charts/styles.css";
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

/** App shell: MantineProvider → QueryClientProvider → App. Query defaults aligned with admin data fetching. */
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
