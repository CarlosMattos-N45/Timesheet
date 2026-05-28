import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Container,
  Typography,
  Box,
  Button,
  Stack,
  TextField,
  Switch,
  FormControlLabel,
  Skeleton,
  Snackbar,
  Alert,
} from "@mui/material";
import { getTerceiroMe, putTerceiroMe, terceirosKeys } from "@/api/terceiros";
import { formatCnpj, unmaskCnpj } from "@/lib/cnpj";
import { parseApiError } from "@/lib/errors";
import { cadastroSchema, type CadastroFormValues } from "@/lib/schemas/cadastro";

function timeToHHmm(t: string): string {
  return t.slice(0, 5);
}

export function CadastroPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [snackbar, setSnackbar] = useState<{
    msg: string;
    severity: "success" | "error";
  } | null>(null);

  const { data: terceiro, isLoading } = useQuery({
    queryKey: terceirosKeys.me,
    queryFn: getTerceiroMe,
  });

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty, isValid, isSubmitting },
  } = useForm<CadastroFormValues>({
    mode: "onBlur",
    resolver: zodResolver(cadastroSchema),
    defaultValues: {
      nome: "",
      empresa_nome: "",
      empresa_cnpj: "",
      inicio: "",
      saidaAlmoco: "",
      retornoAlmoco: "",
      fim: "",
      trabalha_fim_de_semana: false,
      email_contato: "",
      email_destinatario_relatorio: "",
    },
  });

  useEffect(() => {
    if (terceiro) {
      reset({
        nome: terceiro.nome,
        empresa_nome: terceiro.empresa_nome,
        empresa_cnpj: formatCnpj(terceiro.empresa_cnpj),
        inicio: timeToHHmm(terceiro.horario_inicio_jornada),
        saidaAlmoco: timeToHHmm(terceiro.horario_saida_almoco),
        retornoAlmoco: timeToHHmm(terceiro.horario_retorno_almoco),
        fim: timeToHHmm(terceiro.horario_fim_jornada),
        trabalha_fim_de_semana: terceiro.trabalha_fim_de_semana,
        email_contato: terceiro.email_contato,
        email_destinatario_relatorio: terceiro.email_destinatario_relatorio ?? "",
      });
    }
  }, [terceiro, reset]);

  const mutation = useMutation({
    mutationFn: async (v: CadastroFormValues) =>
      putTerceiroMe({
        nome: v.nome,
        empresa_nome: v.empresa_nome,
        empresa_cnpj: unmaskCnpj(v.empresa_cnpj),
        horario_inicio_jornada: `${v.inicio}:00`,
        horario_saida_almoco: `${v.saidaAlmoco}:00`,
        horario_retorno_almoco: `${v.retornoAlmoco}:00`,
        horario_fim_jornada: `${v.fim}:00`,
        trabalha_fim_de_semana: v.trabalha_fim_de_semana,
        email_contato: v.email_contato,
        email_destinatario_relatorio: v.email_destinatario_relatorio || null,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: terceirosKeys.me });
      setSnackbar({ msg: "Cadastro atualizado com sucesso.", severity: "success" });
    },
    onError: (e) => {
      setSnackbar({ msg: parseApiError(e).message, severity: "error" });
    },
  });

  if (isLoading)
    return (
      <Container sx={{ mt: 2 }}>
        <Skeleton variant="rectangular" height={400} />
      </Container>
    );

  return (
    <Container maxWidth="md" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Meu Cadastro
      </Typography>
      <Box component="form" onSubmit={handleSubmit((v) => mutation.mutate(v))}>
        <TextField
          label="Nome"
          fullWidth
          margin="normal"
          {...register("nome")}
          error={Boolean(errors.nome)}
          helperText={errors.nome?.message ?? " "}
        />
        <TextField
          label="Empresa"
          fullWidth
          margin="normal"
          {...register("empresa_nome")}
          error={Boolean(errors.empresa_nome)}
          helperText={errors.empresa_nome?.message ?? " "}
        />
        <Controller
          control={control}
          name="empresa_cnpj"
          render={({ field }) => (
            <TextField
              label="CNPJ"
              fullWidth
              margin="normal"
              value={field.value}
              onChange={(e) => field.onChange(formatCnpj(e.target.value))}
              onBlur={field.onBlur}
              inputProps={{ maxLength: 18, "aria-invalid": Boolean(errors.empresa_cnpj) }}
              error={Boolean(errors.empresa_cnpj)}
              helperText={errors.empresa_cnpj?.message ?? " "}
            />
          )}
        />
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          {(
            [
              ["inicio", "Início"],
              ["saidaAlmoco", "Saída Almoço"],
              ["retornoAlmoco", "Retorno Almoço"],
              ["fim", "Fim"],
            ] as const
          ).map(([n, label]) => (
            <TextField
              key={n}
              label={label}
              type="time"
              {...register(n)}
              error={Boolean(errors[n])}
              helperText={errors[n]?.message ?? " "}
              InputLabelProps={{ shrink: true }}
              sx={{ flex: 1 }}
            />
          ))}
        </Stack>
        <Controller
          control={control}
          name="trabalha_fim_de_semana"
          render={({ field }) => (
            <FormControlLabel
              control={
                <Switch checked={field.value} onChange={(_e, c) => field.onChange(c)} />
              }
              label="Trabalha nos fins de semana"
              sx={{ mt: 1 }}
            />
          )}
        />
        <TextField
          label="E-mail de contato"
          type="email"
          fullWidth
          margin="normal"
          {...register("email_contato")}
          error={Boolean(errors.email_contato)}
          helperText={errors.email_contato?.message ?? " "}
        />
        <TextField
          label="E-mail destinatário do relatório"
          type="email"
          fullWidth
          margin="normal"
          {...register("email_destinatario_relatorio")}
          error={Boolean(errors.email_destinatario_relatorio)}
          helperText={errors.email_destinatario_relatorio?.message ?? "Opcional"}
        />

        <Stack direction="row" spacing={2} mt={3}>
          <Button onClick={() => navigate("/cadastro/senha")}>Alterar senha</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={!isDirty || !isValid || isSubmitting || mutation.isPending}
          >
            {mutation.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </Stack>
      </Box>
      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={5000}
        onClose={() => setSnackbar(null)}
      >
        <Alert
          severity={snackbar?.severity ?? "info"}
          onClose={() => setSnackbar(null)}
          role={snackbar?.severity === "error" ? "alert" : "status"}
        >
          {snackbar?.msg}
        </Alert>
      </Snackbar>
    </Container>
  );
}
