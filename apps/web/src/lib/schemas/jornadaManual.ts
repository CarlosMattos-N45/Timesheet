import { z } from "zod";
import dayjs from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat";

dayjs.extend(customParseFormat);

const horarioRegex = /^([01]\d|2[0-3]):[0-5]\d$/;

const horarioField = z.string().regex(horarioRegex, "Horário inválido (use HH:MM)");

export const jornadaManualSchema = z
  .object({
    data: z.string().min(1, "Data obrigatória").refine(
      (v) => {
        const d = dayjs(v, "YYYY-MM-DD", true);
        return d.isValid() && !d.isAfter(dayjs(), "day");
      },
      { message: "Data inválida ou futura" }
    ),
    inicio: horarioField,
    saidaAlmoco: horarioField,
    retornoAlmoco: horarioField,
    fim: horarioField,
    atividade: z.string().min(10, "Mínimo 10 caracteres").max(2000, "Máximo 2000 caracteres"),
    motivo: z.string().min(5, "Mínimo 5 caracteres").max(500, "Máximo 500 caracteres"),
  })
  .refine(
    (v) =>
      v.inicio < v.saidaAlmoco &&
      v.saidaAlmoco < v.retornoAlmoco &&
      v.retornoAlmoco < v.fim,
    { message: "Os horários devem ser em ordem cronológica.", path: ["saidaAlmoco"] }
  );

export type JornadaManualFormValues = z.infer<typeof jornadaManualSchema>;
