import { useState, useMemo } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, Link as RouterLink } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import {
  Container,
  Typography,
  Box,
  Button,
  Stack,
  TextField,
  Alert,
  Link,
} from "@mui/material";
import { DatePicker, LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { postJornadaManual, jornadasKeys } from "@/api/jornadas";
import { calculaTotalDiario, formatTotal, horarioParaIsoUtc } from "@/lib/format/horario";
import { parseApiError } from "@/lib/errors";
import {
  jornadaManualSchema,
  type JornadaManualFormValues,
} from "@/lib/schemas/jornadaManual";

const TIPOS_LABEL = [
  { field: "inicio", label: "Horário de início" },
  { field: "saidaAlmoco", label: "Horário de saída do almoço" },
  { field: "retornoAlmoco", label: "Horário de retorno do almoço" },
  { field: "fim", label: "Horário de fim" },
] as const;


export function JornadaManualPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [serverError, setServerError] = useState<{
    code: string;
    message: string;
  } | null>(null);

  const {
    control,
    register,
    handleSubmit,
    watch,
    formState: { errors, isValid, isSubmitting },
  } = useForm<JornadaManualFormValues>({
    mode: "all",
    resolver: zodResolver(jornadaManualSchema),
    defaultValues: {
      data: dayjs().format("YYYY-MM-DD"),
      inicio: "",
      saidaAlmoco: "",
      retornoAlmoco: "",
      fim: "",
      atividade: "",
      motivo: "",
    },
  });

  const inicio = watch("inicio");
  const saidaAlmoco = watch("saidaAlmoco");
  const retornoAlmoco = watch("retornoAlmoco");
  const fim = watch("fim");
  const dataSel = watch("data");

  const totalPreview = useMemo(() => {
    if (!inicio || !saidaAlmoco || !retornoAlmoco || !fim || !dataSel) return null;
    try {
      return calculaTotalDiario(
        horarioParaIsoUtc(dataSel, inicio),
        horarioParaIsoUtc(dataSel, saidaAlmoco),
        horarioParaIsoUtc(dataSel, retornoAlmoco),
        horarioParaIsoUtc(dataSel, fim)
      );
    } catch {
      return null;
    }
  }, [dataSel, inicio, saidaAlmoco, retornoAlmoco, fim]);

  const mutation = useMutation({
    mutationFn: (values: JornadaManualFormValues) =>
      postJornadaManual({
        data: values.data,
        marcacoes: [
          {
            tipo: "INICIO_JORNADA",
            horario_efetivo: horarioParaIsoUtc(values.data, values.inicio),
          },
          {
            tipo: "SAIDA_ALMOCO",
            horario_efetivo: horarioParaIsoUtc(values.data, values.saidaAlmoco),
          },
          {
            tipo: "RETORNO_ALMOCO",
            horario_efetivo: horarioParaIsoUtc(values.data, values.retornoAlmoco),
          },
          {
            tipo: "FIM_JORNADA",
            horario_efetivo: horarioParaIsoUtc(values.data, values.fim),
          },
        ],
        atividade: values.atividade,
        motivo: values.motivo,
      }),
    onSuccess: (resp) => {
      const mesNovo = resp.data.slice(0, 7);
      void qc.invalidateQueries({ queryKey: jornadasKeys.lista(mesNovo) });
      void qc.invalidateQueries({ queryKey: jornadasKeys.all });
      navigate(`/jornadas/${resp.id}`, { replace: true });
    },
    onError: (err) => {
      setServerError(parseApiError(err));
    },
  });

  const atividadeVal = watch("atividade");
  const motivoVal = watch("motivo");

  return (
    <Container maxWidth="md" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Nova Jornada Manual
      </Typography>

      <Box
        component="form"
        onSubmit={handleSubmit((v) => {
          setServerError(null);
          mutation.mutate(v);
        })}
      >
        <Controller
          name="data"
          control={control}
          render={({ field }) => (
            <LocalizationProvider dateAdapter={AdapterDayjs}>
              <DatePicker
                label="Data"
                value={field.value ? dayjs(field.value) : null}
                onChange={(v) => {
                  if (v && v.isValid()) {
                    field.onChange(v.format("YYYY-MM-DD"));
                  }
                }}
                maxDate={dayjs()}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    margin: "normal",
                    error: Boolean(errors.data),
                    helperText: errors.data?.message ?? " ",
                    inputProps: {
                      "aria-label": "Data",
                    },
                    onBlur: field.onBlur,
                  },
                }}
              />
            </LocalizationProvider>
          )}
        />

        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 1 }}>
          {TIPOS_LABEL.map(({ field, label }) => (
            <TextField
              key={field}
              label={label}
              fullWidth
              placeholder="HH:MM"
              {...register(field)}
              error={Boolean(errors[field])}
              helperText={errors[field]?.message ?? " "}
              InputLabelProps={{ shrink: true }}
              inputProps={{
                "aria-label": label,
                maxLength: 5,
              }}
            />
          ))}
        </Stack>

        <Typography variant="body1" mt={2}>
          Total:{" "}
          <strong>{formatTotal(totalPreview)}</strong>
        </Typography>

        <TextField
          label="Atividade"
          multiline
          minRows={3}
          fullWidth
          margin="normal"
          {...register("atividade")}
          error={Boolean(errors.atividade)}
          helperText={errors.atividade?.message ?? `${atividadeVal.length}/2000`}
          inputProps={{ "aria-label": "Atividade" }}
        />

        <TextField
          label="Justificativa"
          multiline
          minRows={2}
          fullWidth
          margin="normal"
          {...register("motivo")}
          error={Boolean(errors.motivo)}
          helperText={errors.motivo?.message ?? `${motivoVal.length}/500`}
          inputProps={{ "aria-label": "Justificativa" }}
        />

        {serverError && (
          <Alert severity="error" role="alert" sx={{ mt: 2 }}>
            {serverError.code === "CONFLICT"
              ? "Já existe uma jornada para este dia. Abra-a para editar."
              : serverError.message}
            {serverError.code === "CONFLICT" && (
              <Link component={RouterLink} to="/jornadas" sx={{ ml: 1 }}>
                Voltar para Jornadas
              </Link>
            )}
          </Alert>
        )}

        <Stack direction="row" spacing={2} mt={3}>
          <Button onClick={() => navigate("/jornadas")}>Cancelar</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={!isValid || isSubmitting || mutation.isPending}
          >
            {mutation.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </Stack>
      </Box>
    </Container>
  );
}
