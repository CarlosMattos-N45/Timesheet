import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider, createTheme } from "@mui/material";
import { AuthProvider } from "@/auth/AuthContext";
import { router as appRouter } from "@/routes";

// O router de produção usa createBrowserRouter, incompatível com jsdom em testes.
// Recriamos as routes com createMemoryRouter para testar o comportamento de roteamento.
const testRouter = createMemoryRouter(appRouter.routes, { initialEntries: ["/login"] });
const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
const theme = createTheme({ palette: { mode: "light" } });

function TestApp() {
  return (
    <ThemeProvider theme={theme}>
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <RouterProvider router={testRouter} />
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

describe("App (via routes)", () => {
  it("renderiza a tela de Login (stub) na rota inicial /login", () => {
    render(<TestApp />);
    expect(screen.getByRole("heading", { name: /Login/i })).toBeInTheDocument();
  });
});
