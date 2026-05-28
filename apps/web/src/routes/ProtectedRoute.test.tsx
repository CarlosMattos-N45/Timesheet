import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthContext";
import { ProtectedRoute } from "@/routes/ProtectedRoute";

describe("ProtectedRoute", () => {
  beforeEach(() => sessionStorage.clear());

  it("redireciona para /login quando não autenticado", () => {
    render(
      <MemoryRouter initialEntries={["/jornadas"]}>
        <AuthProvider>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route path="/jornadas" element={<div>JornadasOK</div>} />
            </Route>
            <Route path="/login" element={<div>LoginPage</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.getByText("LoginPage")).toBeInTheDocument();
  });

  it("renderiza Outlet quando autenticado", () => {
    sessionStorage.setItem("ts:access_token", "atok");
    sessionStorage.setItem("ts:refresh_token", "rtok");
    sessionStorage.setItem("ts:terceiro_id", "uuid");
    sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
    render(
      <MemoryRouter initialEntries={["/jornadas"]}>
        <AuthProvider>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route path="/jornadas" element={<div>JornadasOK</div>} />
            </Route>
            <Route path="/login" element={<div>LoginPage</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.getByText("JornadasOK")).toBeInTheDocument();
  });
});
