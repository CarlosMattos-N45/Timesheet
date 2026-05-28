import { z } from "zod";

export const smtpConfigSchema = z.object({
  host: z.string().min(1, "Host obrigatório").max(253, "Máximo 253 caracteres"),
  port: z.coerce.number().int().min(1, "Porta inválida").max(65535, "Porta inválida"),
  username: z.string().min(1, "Usuário obrigatório").max(254, "Máximo 254 caracteres"),
  password: z.string().min(1, "Senha obrigatória").max(512, "Máximo 512 caracteres"),
  use_starttls: z.boolean(),
  from_address: z.string().email("E-mail inválido"),
});

export type SmtpConfigFormValues = z.infer<typeof smtpConfigSchema>;
