import { z } from "zod";
import { isValidCnpj, unmaskCnpj } from "@/lib/cnpj";

const horarioRegex = /^([01]\d|2[0-3]):[0-5]\d$/;
const horarioField = z.string().regex(horarioRegex, "Horário inválido (use HH:MM)");

export const cadastroSchema = z
  .object({
    nome: z.string().min(1, "Nome obrigatório").max(120, "Máximo 120 caracteres"),
    empresa_nome: z.string().min(1, "Empresa obrigatória").max(150, "Máximo 150 caracteres"),
    empresa_cnpj: z
      .string()
      .transform(unmaskCnpj)
      .refine(isValidCnpj, "CNPJ inválido (dígito verificador incorreto)."),
    inicio: horarioField,
    saidaAlmoco: horarioField,
    retornoAlmoco: horarioField,
    fim: horarioField,
    trabalha_fim_de_semana: z.boolean(),
    email_contato: z.string().email("E-mail inválido").max(254),
    email_destinatario_relatorio: z
      .union([z.literal(""), z.string().email("E-mail inválido")])
      .optional(),
  })
  .refine(
    (v) =>
      v.inicio < v.saidaAlmoco &&
      v.saidaAlmoco < v.retornoAlmoco &&
      v.retornoAlmoco < v.fim,
    { message: "Os horários devem ser em ordem cronológica.", path: ["saidaAlmoco"] }
  );

export type CadastroFormValues = z.infer<typeof cadastroSchema>;

export const senhaSchema = z
  .object({
    senha_atual: z.string().min(1, "Senha atual obrigatória"),
    nova_senha: z.string().min(8, "Mínimo 8 caracteres").max(128, "Máximo 128 caracteres"),
    confirmar_senha: z.string().min(1, "Confirmação obrigatória"),
  })
  .refine((v) => v.nova_senha === v.confirmar_senha, {
    message: "As senhas não coincidem",
    path: ["confirmar_senha"],
  });

export type SenhaFormValues = z.infer<typeof senhaSchema>;
