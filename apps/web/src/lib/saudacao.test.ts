import { describe, it, expect } from "vitest";
import { saudacaoPorHora } from "@/lib/saudacao";

describe("saudacaoPorHora", () => {
  it("0 a 11 → Bom dia", () => {
    expect(saudacaoPorHora(0)).toBe("Bom dia");
    expect(saudacaoPorHora(11)).toBe("Bom dia");
  });
  it("12 a 17 → Boa tarde", () => {
    expect(saudacaoPorHora(12)).toBe("Boa tarde");
    expect(saudacaoPorHora(17)).toBe("Boa tarde");
  });
  it("18 a 23 → Boa noite", () => {
    expect(saudacaoPorHora(18)).toBe("Boa noite");
    expect(saudacaoPorHora(23)).toBe("Boa noite");
  });
});
