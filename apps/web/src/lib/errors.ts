import { AxiosError } from "axios";
import type { ApiErrorBody } from "@/types/contracts";

export interface ParsedApiError {
  code: string;
  message: string;
  fields: Record<string, string>;
}

const FIELD_PREFIX = /^body\./;

export function parseApiError(err: unknown): ParsedApiError {
  if (err instanceof AxiosError) {
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
