const PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
const PESOS_DV2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

function calcDV(digits: number[], pesos: number[]): number {
  const soma = digits.reduce((acc, d, i) => acc + d * pesos[i]!, 0);
  const resto = soma % 11;
  return resto < 2 ? 0 : 11 - resto;
}

export function isValidCnpj(value: string): boolean {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 14) return false;
  if (/^(\d)\1{13}$/.test(digits)) return false; // todos iguais
  const arr = digits.split("").map(Number);
  const dv1 = calcDV(arr.slice(0, 12), PESOS_DV1);
  if (dv1 !== arr[12]) return false;
  const dv2 = calcDV(arr.slice(0, 13), PESOS_DV2);
  return dv2 === arr[13];
}

export function formatCnpj(value: string): string {
  const d = value.replace(/\D/g, "").slice(0, 14);
  // Máscara: XX.XXX.XXX/XXXX-XX
  // Separador é inserido apenas quando o grupo que vem a seguir está completo
  if (d.length < 6) return d;
  if (d.length < 9) return `${d.slice(0, 2)}.${d.slice(2)}`;
  if (d.length < 13) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5)}`;
  if (d.length < 14) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8)}`;
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}

export function unmaskCnpj(value: string): string {
  return value.replace(/\D/g, "");
}
