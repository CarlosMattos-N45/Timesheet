import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import MockAdapter from "axios-mock-adapter";
import React from "react";
import api from "@/api/client";
import { AuthProvider, useAuth } from "@/auth/AuthContext";

const mock = new MockAdapter(api);

describe("AuthContext", () => {
  beforeEach(() => {
    sessionStorage.clear();
    mock.reset();
  });

  it("login persiste tokens no sessionStorage e marca autenticado", async () => {
    mock.onPost("/api/v1/auth/login").reply(200, {
      access_token: "atok",
      refresh_token: "rtok",
      terceiro_id: "uuid-1",
      expires_in: 900,
    });
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(false);
    await act(async () => {
      await result.current.login("maria@acme.com", "MinhaSenha123!");
    });
    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));
    expect(result.current.terceiroId).toBe("uuid-1");
    expect(sessionStorage.getItem("ts:access_token")).toBe("atok");
    expect(sessionStorage.getItem("ts:refresh_token")).toBe("rtok");
  });

  it("logout limpa sessionStorage e marca desautenticado", async () => {
    sessionStorage.setItem("ts:access_token", "atok");
    sessionStorage.setItem("ts:refresh_token", "rtok");
    sessionStorage.setItem("ts:terceiro_id", "uuid-1");
    sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );
    mock.onPost("/api/v1/auth/logout").reply(204);
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(true);
    act(() => result.current.logout());
    expect(result.current.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem("ts:access_token")).toBeNull();
  });

  it("evento ts:auth-logout zera estado de autenticação", async () => {
    sessionStorage.setItem("ts:access_token", "atok");
    sessionStorage.setItem("ts:refresh_token", "rtok");
    sessionStorage.setItem("ts:terceiro_id", "uuid-1");
    sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(true);
    act(() => {
      window.dispatchEvent(new CustomEvent("ts:auth-logout"));
    });
    await waitFor(() => expect(result.current.isAuthenticated).toBe(false));
  });
});
