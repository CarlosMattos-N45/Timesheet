import { describe, it, expect } from "vitest";
import { formatHoraBR, formatTotal, formatData, formatDiaSemana, calculaTotalDiario } from "@/lib/format/horario";

describe("format/horario", () => {
  describe("formatHoraBR", () => {
    it("12:00Z UTC → 09:00 (UTC-3)", () => {
      expect(formatHoraBR("2026-05-27T12:00:00+00:00")).toBe("09:00");
    });
    it("21:00Z UTC → 18:00 (UTC-3)", () => {
      expect(formatHoraBR("2026-05-27T21:00:00+00:00")).toBe("18:00");
    });
    it("null → '—'", () => {
      expect(formatHoraBR(null)).toBe("—");
    });
  });
  describe("formatTotal", () => {
    it("28800 → '08:00'", () => expect(formatTotal(28800)).toBe("08:00"));
    it("3661 → '01:01'", () => expect(formatTotal(3661)).toBe("01:01"));
    it("null → '—'", () => expect(formatTotal(null)).toBe("—"));
    it("0 → '00:00'", () => expect(formatTotal(0)).toBe("00:00"));
  });
  describe("formatData", () => {
    it("'2026-05-27' → '27/05'", () => expect(formatData("2026-05-27")).toBe("27/05"));
  });
  describe("formatDiaSemana", () => {
    it("'2026-05-27' (quarta) → 'Qua'", () => expect(formatDiaSemana("2026-05-27")).toBe("Qua"));
    it("'2026-05-30' (sábado) → 'Sab'", () => expect(formatDiaSemana("2026-05-30")).toBe("Sab"));
  });
  describe("calculaTotalDiario", () => {
    it("inicio 09:00, saida 12:00, retorno 13:00, fim 18:00 → 28800", () => {
      // 09:00 = 2026-05-27T09:00:00 local (BRT = UTC-3) → UTC T12:00
      // saida 12:00 BRT → UTC T15:00
      // retorno 13:00 BRT → UTC T16:00
      // fim 18:00 BRT → UTC T21:00
      // total = (21 - 12) - (16 - 15) = 9h - 1h = 8h = 28800s
      expect(calculaTotalDiario(
        "2026-05-27T12:00:00Z",
        "2026-05-27T15:00:00Z",
        "2026-05-27T16:00:00Z",
        "2026-05-27T21:00:00Z"
      )).toBe(28800);
    });
    it("null inicio → null", () => {
      expect(calculaTotalDiario(null, null, null, "2026-05-27T21:00:00Z")).toBeNull();
    });
    it("null fim → null", () => {
      expect(calculaTotalDiario("2026-05-27T12:00:00Z", null, null, null)).toBeNull();
    });
    it("fim <= inicio → null", () => {
      expect(calculaTotalDiario("2026-05-27T21:00:00Z", null, null, "2026-05-27T12:00:00Z")).toBeNull();
    });
    it("sem almoço → (fim - inicio)", () => {
      // 12:00 → 21:00 = 9h = 32400s
      expect(calculaTotalDiario("2026-05-27T12:00:00Z", null, null, "2026-05-27T21:00:00Z")).toBe(32400);
    });
  });
});
