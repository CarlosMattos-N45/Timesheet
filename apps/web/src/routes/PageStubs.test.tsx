import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/test/render";
import {
  LoginPageStub,
  PrivacidadePageStub,
  JornadasPageStub,
  JornadaDetalhePageStub,
  JornadaManualPageStub,
  CadastroPageStub,
  SenhaPageStub,
} from "@/routes/PageStubs";

describe("PageStubs", () => {
  it("LoginPageStub renderiza heading com label", () => {
    renderWithProviders(<LoginPageStub />);
    expect(screen.getByText("Login")).toBeInTheDocument();
  });

  it("PrivacidadePageStub renderiza heading", () => {
    renderWithProviders(<PrivacidadePageStub />);
    expect(screen.getByText("Privacidade")).toBeInTheDocument();
  });

  it("JornadasPageStub renderiza heading", () => {
    renderWithProviders(<JornadasPageStub />);
    expect(screen.getByText("Jornadas")).toBeInTheDocument();
  });

  it("JornadaDetalhePageStub renderiza heading", () => {
    renderWithProviders(<JornadaDetalhePageStub />);
    expect(screen.getByText("Detalhe da Jornada")).toBeInTheDocument();
  });

  it("JornadaManualPageStub renderiza heading", () => {
    renderWithProviders(<JornadaManualPageStub />);
    expect(screen.getByText("Nova Jornada Manual")).toBeInTheDocument();
  });

  it("CadastroPageStub renderiza heading", () => {
    renderWithProviders(<CadastroPageStub />);
    expect(screen.getByText("Cadastro")).toBeInTheDocument();
  });

  it("SenhaPageStub renderiza heading", () => {
    renderWithProviders(<SenhaPageStub />);
    expect(screen.getByText("Alterar Senha")).toBeInTheDocument();
  });
});
