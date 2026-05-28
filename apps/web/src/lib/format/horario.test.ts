import { describe, it, expect } from "vitest";
import { formatHoraBR, formatTotal, formatData, formatDiaSemana } from "@/lib/format/horario";

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
});
