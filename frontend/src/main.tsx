import "@mantine/core/styles.css";
import "./index.css";

import { ColorSchemeScript, MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { appTheme } from "./theme";
import { registerPwa } from "./pwa/registerPwa";

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
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={appTheme} defaultColorScheme="light">
        <App />
      </MantineProvider>
    </QueryClientProvider>
  </React.StrictMode>
);

registerPwa();
