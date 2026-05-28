import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Container,
  Typography,
  Box,
  Stack,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Alert,
  Snackbar,
  Skeleton,
} from "@mui/material";
import { getSmtpConfig, putSmtpConfig, postTestSmtp, smtpKeys } from "@/api/smtp";
import { parseApiError } from "@/lib/errors";
import { smtpConfigSchema, type SmtpConfigFormValues } from "@/lib/schemas/smtp";

const MENSAGENS: Partial<Record<string, string>> = {
  SMTP_NOT_CONFIGURED: "SMTP não configurado. Salve antes de testar.",
  SMTP_TEST_FAILED: "", // passthrough: usa mensagem real do backend
};

export function SmtpConfigPage() {
  const qc = useQueryClient();
  const [snackbar, setSnackbar] = useState<{
    msg: string;
    severity: "success" | "error" | "info";
  } | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: smtpKeys.config,
    queryFn: getSmtpConfig,
    retry: false,
  });

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<SmtpConfigFormValues>({
    mode: "onBlur",
    resolver: zodResolver(smtpConfigSchema),
    defaultValues: {
      host: "",
      port: 587,
      username: "",
      password: "",
      use_starttls: true,
      from_address: "",
    },
  });

  useEffect(() => {
    if (data) {
      reset({
        host: data.host,
        port: data.port,
        username: data.username,
        password: "", // senha não vem do backend
        use_starttls: data.use_starttls,
        from_address: data.from_address,
      });
    }
  }, [data, reset]);

  const putMut = useMutation({
    mutationFn: (v: SmtpConfigFormValues) =>
      putSmtpConfig({
        host: v.host,
        port: v.port,
        username: v.username,
        password: v.password,
        use_starttls: v.use_starttls,
        from_address: v.from_address,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: smtpKeys.config });
      setSnackbar({ msg: "Configuração SMTP salva.", severity: "success" });
    },
    onError: (e) => {
      setSnackbar({ msg: parseApiError(e).message, severity: "error" });
    },
  });

  const testMut = useMutation({
    mutationFn: postTestSmtp,
    onSuccess: () => {
      setTestError(null);
      setSnackbar({ msg: "Conexão SMTP testada com sucesso.", severity: "success" });
    },
    onError: (e) => {
      const p = parseApiError(e);
      const mapped = MENSAGENS[p.code];
      const m = mapped !== undefined ? (mapped || p.message) : p.message;
      setTestError(m);
    },
  });

  return (
    <Container maxWidth="md" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Configuração SMTP
      </Typography>

      {isError && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Nenhuma configuração salva ainda.
        </Alert>
      )}

      {isLoading ? (
        <Skeleton variant="rectangular" height={400} />
      ) : (
        <Box component="form" onSubmit={handleSubmit((v) => putMut.mutate(v))}>
          <TextField
            label="Host"
            fullWidth
            margin="normal"
            {...register("host")}
            error={Boolean(errors.host)}
            helperText={errors.host?.message ?? " "}
          />
          <TextField
            label="Porta"
            type="number"
            fullWidth
            margin="normal"
            inputProps={{ min: 1, max: 65535 }}
            {...register("port", { valueAsNumber: true })}
            error={Boolean(errors.port)}
            helperText={errors.port?.message ?? " "}
          />
          <TextField
            label="Usuário"
            fullWidth
            margin="normal"
            {...register("username")}
            error={Boolean(errors.username)}
            helperText={errors.username?.message ?? " "}
          />
          <TextField
            label="Senha"
            type="password"
            fullWidth
            margin="normal"
            {...register("password")}
            error={Boolean(errors.password)}
            helperText={errors.password?.message ?? " "}
          />
          <Controller
            control={control}
            name="use_starttls"
            render={({ field }) => (
              <FormControlLabel
                control={
                  <Switch
                    checked={field.value}
                    onChange={(_e, c) => field.onChange(c)}
                  />
                }
                label="STARTTLS"
              />
            )}
          />
          <TextField
            label="From address"
            type="email"
            fullWidth
            margin="normal"
            {...register("from_address")}
            error={Boolean(errors.from_address)}
            helperText={errors.from_address?.message ?? " "}
          />

          {testError && (
            <Alert severity="error" role="alert" sx={{ mt: 2 }}>
              {testError}
            </Alert>
          )}

          <Stack direction="row" spacing={2} mt={3}>
            <Button onClick={() => testMut.mutate()} disabled={testMut.isPending}>
              {testMut.isPending ? "Testando..." : "Testar conexão"}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={isSubmitting || putMut.isPending}
            >
              {putMut.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </Stack>
        </Box>
      )}

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
