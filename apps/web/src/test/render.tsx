import { useEffect, type ReactElement, type ReactNode } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider, createTheme } from "@mui/material";
import { AuthProvider } from "@/auth/AuthContext";
import { STORAGE } from "@/api/client";

interface ProviderOpts {
  route?: string;
  authState?: {
    accessToken?: string;
    refreshToken?: string;
    terceiroId?: string;
    terceiroNome?: string;
  };
}

/** Sincroniza MemoryRouter com window.location para que testes de navegação
 *  possam verificar window.location.pathname após navigate() */
function LocationSync() {
  const location = useLocation();
  useEffect(() => {
    window.history.replaceState(null, "", location.pathname + location.search + location.hash);
  }, [location]);
  return null;
}

export function renderWithProviders(
  ui: ReactElement,
  opts: ProviderOpts = {},
  rOpts: Omit<RenderOptions, "wrapper"> = {}
) {
  if (opts.authState) {
    const { accessToken, refreshToken, terceiroId } = opts.authState;
    if (accessToken) sessionStorage.setItem(STORAGE.accessToken, accessToken);
    if (refreshToken) sessionStorage.setItem(STORAGE.refreshToken, refreshToken);
    if (terceiroId) sessionStorage.setItem(STORAGE.terceiroId, terceiroId);
    sessionStorage.setItem(STORAGE.expiresAt, String(Date.now() + 60_000));
  }
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const theme = createTheme({ palette: { mode: "light" } });
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <ThemeProvider theme={theme}>
      <MemoryRouter initialEntries={[opts.route ?? "/"]}>
        <LocationSync />
        <QueryClientProvider client={qc}>
          <AuthProvider>{children}</AuthProvider>
        </QueryClientProvider>
      </MemoryRouter>
    </ThemeProvider>
  );
  return render(ui, { wrapper: Wrapper, ...rOpts });
}
