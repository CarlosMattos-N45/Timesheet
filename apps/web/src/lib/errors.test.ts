import { describe, it, expect } from "vitest";
import { parseApiError } from "@/lib/errors";
import { AxiosError } from "axios";

describe("parseApiError", () => {
  it("extrai code, message e fields (strip body. prefix)", () => {
    const err = new AxiosError("Request failed");
    (err as unknown as { response: unknown }).response = {
      data: {
        code: "VALIDATION_ERROR",
        message: "Erro de validação",
        details: [
          { field: "body.empresa_cnpj", issue: "CNPJ inválido" },
          { field: "body.senha", issue: "muito curta" },
        ],
      },
    };
    expect(parseApiError(err)).toEqual({
      code: "VALIDATION_ERROR",
      message: "Erro de validação",
      fields: { empresa_cnpj: "CNPJ inválido", senha: "muito curta" },
    });
  });
  it("erro de rede sem response retorna code=NETWORK_ERROR", () => {
    const err = new AxiosError("Network Error");
    expect(parseApiError(err)).toEqual({
      code: "NETWORK_ERROR",
      message: "Falha de conexão. Verifique o serviço local.",
      fields: {},
    });
  });
});
