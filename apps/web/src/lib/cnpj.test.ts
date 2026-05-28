import { describe, it, expect } from "vitest";
import { isValidCnpj, formatCnpj, unmaskCnpj } from "@/lib/cnpj";

describe("cnpj", () => {
  describe("isValidCnpj", () => {
    it("'00000000000191' (CNPJ válido público — Banco do Brasil) → true", () => {
      expect(isValidCnpj("00000000000191")).toBe(true);
    });
    it("'11444777000161' (Petrobras) → true", () => {
      expect(isValidCnpj("11444777000161")).toBe(true);
    });
    it("'00000000000000' (todos zero) → false", () => {
      expect(isValidCnpj("00000000000000")).toBe(false);
    });
    it("'11111111111111' (todos iguais) → false", () => {
      expect(isValidCnpj("11111111111111")).toBe(false);
    });
    it("'00000000000200' (DV incorreto) → false", () => {
      expect(isValidCnpj("00000000000200")).toBe(false);
    });
    it("'00.000.000/0001-91' (com máscara) → true (strip)", () => {
      expect(isValidCnpj("00.000.000/0001-91")).toBe(true);
    });
    it("string vazia → false", () => {
      expect(isValidCnpj("")).toBe(false);
    });
  });
  describe("formatCnpj", () => {
    it("'00000000000191' → '00.000.000/0001-91'", () => {
      expect(formatCnpj("00000000000191")).toBe("00.000.000/0001-91");
    });
    it("'123' → '123'", () => expect(formatCnpj("123")).toBe("123"));
    it("'0000000000019100' (>14 dígitos) → trunca para 14 e formata", () => {
      expect(formatCnpj("0000000000019100")).toBe("00.000.000/0001-91");
    });
  });
  describe("unmaskCnpj", () => {
    it("'00.000.000/0001-91' → '00000000000191'", () => {
      expect(unmaskCnpj("00.000.000/0001-91")).toBe("00000000000191");
    });
  });
});
