import { z } from "zod";

export const ajusteSchema = z.object({
  motivo: z.string().min(5, "Mínimo 5 caracteres").max(500, "Máximo 500 caracteres"),
});
export type AjusteFormValues = z.infer<typeof ajusteSchema>;

export const atividadeSchema = z.object({
  descricao: z.string().min(10, "Mínimo 10 caracteres").max(2000, "Máximo 2000 caracteres"),
});
export type AtividadeFormValues = z.infer<typeof atividadeSchema>;
