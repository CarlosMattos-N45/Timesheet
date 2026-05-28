export type Saudacao = "Bom dia" | "Boa tarde" | "Boa noite";

export function saudacaoPorHora(h: number): Saudacao {
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

export function saudacaoAgora(now: Date = new Date()): Saudacao {
  return saudacaoPorHora(now.getHours());
}
