import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { PrivacidadePage } from "@/pages/Privacidade/PrivacidadePage";
import { privacidadeKeys } from "@/api/privacidade";

const mock = new MockAdapter(api);

describe("PrivacidadePage", () => {
  beforeEach(() => {
    mock.reset();
    sessionStorage.clear();
  });

  it("renderiza heading h1 'Aviso de Privacidade' e bloco com termos", () => {
    renderWithProviders(<PrivacidadePage />, { route: "/privacidade" });
    expect(screen.getByRole("heading", { level: 1, name: /Aviso de Privacidade/i })).toBeInTheDocument();
    expect(screen.getByText(/Dados coletados/i)).toBeInTheDocument();
    expect(screen.getByText(/email_destinatario_relatorio/i)).toBeInTheDocument();
    expect(screen.getByText(/AES-GCM/i)).toBeInTheDocument();
  });

  it("botão Continuar inicia com aria-disabled=true e habilita ao marcar o checkbox", async () => {
    renderWithProviders(<PrivacidadePage />, { route: "/privacidade" });
    const btn = screen.getByRole("button", { name: /Continuar/i });
    expect(btn).toBeDisabled();
    const chk = screen.getByRole("checkbox", { name: /Li e aceito os termos de privacidade/i });
    await userEvent.click(chk);
    expect(chk).toBeChecked();
    expect(btn).toBeEnabled();
  });

  it("clique em Continuar chama POST /api/v1/privacidade/aceitar e invalida o cache", async () => {
    let postCalled = false;
    mock.onPost("/api/v1/privacidade/aceitar").reply(() => {
      postCalled = true;
      return [204, ""];
    });
    const { queryClient } = renderWithProviders(<PrivacidadePage />, { route: "/privacidade" });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /Continuar/i }));
    await waitFor(() => expect(postCalled).toBe(true));
    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: privacidadeKeys.status })
    );
  });

  it("erro do POST exibe snackbar com texto exato 'Não foi possível registrar o aceite. Tente novamente.'", async () => {
    mock.onPost("/api/v1/privacidade/aceitar").reply(500, {
      code: "INTERNAL_ERROR", message: "boom", details: [],
    });
    renderWithProviders(<PrivacidadePage />, { route: "/privacidade" });
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /Continuar/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Não foi possível registrar o aceite\. Tente novamente\./i);
  });

  it("checkbox tem aria-checked=true ao marcar", async () => {
    renderWithProviders(<PrivacidadePage />, { route: "/privacidade" });
    const chk = screen.getByRole("checkbox");
    expect(chk).toHaveAttribute("aria-checked", "false");
    await userEvent.click(chk);
    expect(chk).toHaveAttribute("aria-checked", "true");
  });
});
