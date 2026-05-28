import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { JornadaDetalhePage } from "@/pages/JornadaDetalhe/JornadaDetalhePage";

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useParams: () => ({ id: "j1" }),
  };
});

const mock = new MockAdapter(api);

const J_FECHADA = {
  id: "j1", data: "2026-05-27", status: "FECHADA",
  total_horas_apuradas_s: 28800,
  marcacoes: [
    { id: "m1", tipo: "INICIO_JORNADA", horario_registrado: "2026-05-27T12:00:00+00:00", horario_efetivo: "2026-05-27T12:00:00+00:00", origem: "AGENTE_AUTOMATICO", status: "CONFIRMADA" },
    { id: "m2", tipo: "SAIDA_ALMOCO", horario_registrado: "2026-05-27T15:00:00+00:00", horario_efetivo: "2026-05-27T15:00:00+00:00", origem: "AGENTE_AUTOMATICO", status: "CONFIRMADA" },
    { id: "m3", tipo: "RETORNO_ALMOCO", horario_registrado: "2026-05-27T16:00:00+00:00", horario_efetivo: "2026-05-27T16:00:00+00:00", origem: "AGENTE_AUTOMATICO", status: "CONFIRMADA" },
    { id: "m4", tipo: "FIM_JORNADA", horario_registrado: "2026-05-27T21:00:00+00:00", horario_efetivo: "2026-05-27T21:00:00+00:00", origem: "AGENTE_CONFIRMADO", status: "CONFIRMADA" },
  ],
  atividade: { id: "a1", jornada_id: "j1", descricao: "Trabalhei no projeto X", registrada_em: "2026-05-27T21:05:00+00:00", atualizado_em: null },
  justificativas: [],
};

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
});

describe("JornadaDetalhePage", () => {
  it("renderiza breadcrumb, chip FECHADA verde, 4 horários e total 08:00", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, J_FECHADA);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    expect(await screen.findByText(/27\/05\/2026/)).toBeInTheDocument();
    expect(screen.getByText("FECHADA")).toBeInTheDocument();
    // Total visível
    expect(screen.getByText(/Total:\s*08:00/i)).toBeInTheDocument();
    // 4 TimePickers presentes pelo aria-label
    expect(screen.getByLabelText(/Horário de início/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Horário de saída do almoço/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Horário de retorno do almoço/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Horário de fim/i)).toBeInTheDocument();
  });

  it("status PENDENTE exibe banner topo e bloqueia TimePickers", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, {
      ...J_FECHADA, status: "PENDENTE",
      marcacoes: [
        ...J_FECHADA.marcacoes.slice(0, 3),
        { ...J_FECHADA.marcacoes[3], status: "PENDENTE" },
      ],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    expect(await screen.findByText(/Esta jornada possui marcações pendentes\./i)).toBeInTheDocument();
    const tp = screen.getByLabelText(/Horário de início/i) as HTMLInputElement;
    expect(tp).toBeDisabled();
  });

  it("salvar alteração abre modal de justificativa; <5 chars desabilita Confirmar; >=5 chars habilita e PUT /jornadas/j1 com motivo + 1 marcação", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, J_FECHADA);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    let putBody: unknown = null;
    mock.onPut("/api/v1/jornadas/j1").reply((c) => {
      putBody = JSON.parse(c.data as string);
      return [200, { ...J_FECHADA, status: "AJUSTADA_MANUALMENTE" }];
    });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    const inicio = await screen.findByLabelText(/Horário de início/i) as HTMLInputElement;
    await userEvent.clear(inicio);
    await userEvent.type(inicio, "08:55");
    await userEvent.tab();
    // Botão Salvar visível
    const btnSalvar = await screen.findByRole("button", { name: /Salvar alterações/i });
    await userEvent.click(btnSalvar);
    // Modal de justificativa aberto
    const motivo = screen.getByLabelText(/Motivo/i) as HTMLTextAreaElement;
    expect(screen.getByRole("button", { name: /Confirmar alterações/i })).toBeDisabled();
    await userEvent.type(motivo, "ajuste de relógio");
    expect(screen.getByRole("button", { name: /Confirmar alterações/i })).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: /Confirmar alterações/i }));
    await waitFor(() => expect(putBody).not.toBeNull());
    expect((putBody as { motivo: string }).motivo).toBe("ajuste de relógio");
    expect((putBody as { marcacoes: unknown[] }).marcacoes).toEqual([
      expect.objectContaining({ tipo: "INICIO_JORNADA" }),
    ]);
  });

  it("422 VALIDATION_ERROR no PUT exibe alert com mensagem do backend dentro do modal", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, J_FECHADA);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    mock.onPut("/api/v1/jornadas/j1").reply(422, {
      code: "VALIDATION_ERROR",
      message: "horários devem ser cronológicos",
      details: [],
    });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    const inicio = await screen.findByLabelText(/Horário de início/i) as HTMLInputElement;
    await userEvent.clear(inicio);
    await userEvent.type(inicio, "19:00");
    await userEvent.tab();
    await userEvent.click(await screen.findByRole("button", { name: /Salvar alterações/i }));
    await userEvent.type(screen.getByLabelText(/Motivo/i), "tentando inverter");
    await userEvent.click(screen.getByRole("button", { name: /Confirmar alterações/i }));
    expect(await screen.findByText(/horários devem ser cronológicos/i)).toBeInTheDocument();
  });

  it("editar atividade e clicar Salvar atividade chama POST /jornadas/j1/atividade", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, J_FECHADA);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    let postBody: unknown = null;
    mock.onPost("/api/v1/jornadas/j1/atividade").reply((c) => {
      postBody = JSON.parse(c.data as string);
      return [201, { id: "a1", jornada_id: "j1", descricao: (postBody as { descricao: string }).descricao, registrada_em: "...", atualizado_em: "..." }];
    });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    const ta = await screen.findByLabelText(/Atividade do dia/i) as HTMLTextAreaElement;
    await userEvent.clear(ta);
    await userEvent.type(ta, "Trabalhei no projeto X com sub-tarefa Y");
    await userEvent.click(screen.getByRole("button", { name: /Salvar atividade/i }));
    await waitFor(() => expect((postBody as { descricao?: string })?.descricao).toBe("Trabalhei no projeto X com sub-tarefa Y"));
  });

  it("expandir accordion Histórico de auditoria carrega GET /auditoria lazy", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, J_FECHADA);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    let auditChamado = false;
    mock.onGet("/api/v1/auditoria").reply(() => {
      auditChamado = true;
      return [200, [{
        id: "log1", entidade: "Jornada", entidade_id: "j1", autor: "maria@acme.com",
        antes_json: '{"x":1}', depois_json: '{"x":2}', motivo: "ajuste",
        criado_em: "2026-05-27T22:00:00+00:00",
      }]];
    });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    expect(auditChamado).toBe(false);
    const acc = await screen.findByRole("button", { name: /Histórico de auditoria/i });
    expect(acc).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(acc);
    await waitFor(() => expect(auditChamado).toBe(true));
    expect(acc).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByText(/maria@acme\.com/i)).toBeInTheDocument();
  });
});
