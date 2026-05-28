import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider, createTheme } from "@mui/material";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { AuthProvider } from "@/auth/AuthContext";
import { PrivacyGuard } from "@/routes/PrivacyGuard";

const mock = new MockAdapter(api);
const theme = createTheme();

function makeWrapper(initialEntry: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper() {
    return (
      <ThemeProvider theme={theme}>
        <QueryClientProvider client={qc}>
          <MemoryRouter initialEntries={[initialEntry]}>
            <AuthProvider>
              <Routes>
                <Route element={<PrivacyGuard />}>
                  <Route path="/jornadas" element={<div>Jornadas</div>} />
                  <Route path="/privacidade" element={<div>Privacidade</div>} />
                </Route>
              </Routes>
            </AuthProvider>
          </MemoryRouter>
        </QueryClientProvider>
      </ThemeProvider>
    );
  };
}

describe("PrivacyGuard", () => {
  beforeEach(() => {
    mock.reset();
    sessionStorage.clear();
  });

  it("redireciona para /privacidade quando accepted=false e rota não é /privacidade", async () => {
    mock.onGet("/api/v1/privacidade").reply(200, { accepted: false, versao_aviso: "1.0", aceito_em: null });
    const Wrapper = makeWrapper("/jornadas");
    render(<div />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByText("Privacidade")).toBeInTheDocument();
    });
  });

  it("permite acesso a /privacidade quando accepted=false", async () => {
    mock.onGet("/api/v1/privacidade").reply(200, { accepted: false, versao_aviso: "1.0", aceito_em: null });
    const Wrapper = makeWrapper("/privacidade");
    render(<div />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByText("Privacidade")).toBeInTheDocument();
    });
  });

  it("redireciona para /jornadas quando accepted=true e rota é /privacidade", async () => {
    mock.onGet("/api/v1/privacidade").reply(200, {
      accepted: true,
      versao_aviso: "1.0",
      aceito_em: "2026-01-01T00:00:00Z",
    });
    const Wrapper = makeWrapper("/privacidade");
    render(<div />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByText("Jornadas")).toBeInTheDocument();
    });
  });

  it("permite acesso a /jornadas quando accepted=true", async () => {
    mock.onGet("/api/v1/privacidade").reply(200, {
      accepted: true,
      versao_aviso: "1.0",
      aceito_em: "2026-01-01T00:00:00Z",
    });
    const Wrapper = makeWrapper("/jornadas");
    render(<div />, { wrapper: Wrapper });
    await waitFor(() => {
      expect(screen.getByText("Jornadas")).toBeInTheDocument();
    });
  });
});
