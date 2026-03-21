import { ReactElement, ReactNode } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { appTheme } from "./theme";

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

type RenderWithProvidersOptions = Omit<RenderOptions, "wrapper"> & {
  /** Wraps children in MemoryRouter (order: Mantine → Query → Router → page). */
  withRouter?: boolean;
};

/**
 * Matches production entry order from `main.tsx`: Mantine → Query → (Router) → UI.
 */
export function renderWithProviders(ui: ReactElement, options?: RenderWithProvidersOptions) {
  const { withRouter, ...renderOptions } = options ?? {};
  const queryClient = createTestQueryClient();

  const Wrapper = ({ children }: { children: ReactNode }) => {
    const routed = withRouter ? (
      <MemoryRouter initialEntries={["/"]}>{children}</MemoryRouter>
    ) : (
      children
    );
    return (
      <MantineProvider theme={appTheme} defaultColorScheme="light">
        <QueryClientProvider client={queryClient}>{routed}</QueryClientProvider>
      </MantineProvider>
    );
  };

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}
