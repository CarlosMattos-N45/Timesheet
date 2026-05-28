import type { ApiErrorBody } from "@/types/contracts";

export interface ParsedApiError {
  code: string;
  message: string;
  fields: Record<string, string>;
}

const FIELD_PREFIX = /^body\./;

interface AxiosLike {
  isAxiosError: boolean;
  response?: { data?: unknown };
}

function isAxiosLike(err: unknown): err is AxiosLike {
  return typeof err === "object" && err !== null && (err as AxiosLike).isAxiosError === true;
}

export function parseApiError(err: unknown): ParsedApiError {
  if (isAxiosLike(err)) {
    const body = err.response?.data as ApiErrorBody | undefined;
    if (body && typeof body === "object" && "code" in body) {
      const fields: Record<string, string> = {};
      for (const d of body.details ?? []) {
        if (d.field) {
          const name = d.field.replace(FIELD_PREFIX, "");
          fields[name] = d.issue ?? "";
        }
      }
      return { code: body.code, message: body.message, fields };
    }
    if (!err.response) {
      return {
        code: "NETWORK_ERROR",
        message: "Falha de conexão. Verifique o serviço local.",
        fields: {},
      };
    }
  }
  return { code: "UNKNOWN_ERROR", message: "Ocorreu um erro inesperado.", fields: {} };
}
