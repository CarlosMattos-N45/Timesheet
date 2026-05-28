import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  Container,
  Typography,
  Box,
  Stack,
  TextField,
  Button,
  Alert,
  Snackbar,
  LinearProgress,
} from "@mui/material";
import { putSenha } from "@/api/terceiros";
import { useAuth } from "@/auth/AuthContext";
import { parseApiError } from "@/lib/errors";
import { senhaSchema, type SenhaFormValues } from "@/lib/schemas/cadastro";

function calcForca(s: string): {
  label: string;
  value: number;
  color: "error" | "warning" | "success";
} {
  if (s.length < 8) return { label: "Fraca", value: 25, color: "error" };
  if (s.length < 14) return { label: "Média", value: 60, color: "warning" };
  return { label: "Forte", value: 100, color: "success" };
}

export function SenhaPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const senhaAtualRef = useRef<HTMLInputElement | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    resetField,
    setFocus,
    formState: { errors, isValid, isSubmitting },
  } = useForm<SenhaFormValues>({
    mode: "onChange",
    resolver: zodResolver(senhaSchema),
    defaultValues: { senha_atual: "", nova_senha: "", confirmar_senha: "" },
  });

  const nova = watch("nova_senha");
  const forca = calcForca(nova);

  const mutation = useMutation({
    mutationFn: async (v: SenhaFormValues) =>
      putSenha({ senha_atual: v.senha_atual, nova_senha: v.nova_senha }),
    onSuccess: () => {
      setSuccess(true);
      setTimeout(() => {
        logout();
        navigate("/login", { replace: true, state: { passwordChanged: true } });
      }, 500);
    },
    onError: (e) => {
      const p = parseApiError(e);
      if (p.code === "UNAUTHORIZED") {
        setServerError("Senha atual incorreta.");
        resetField("senha_atual");
        setTimeout(() => setFocus("senha_atual"), 0);
      } else {
        setServerError(p.message);
      }
    },
  });

  const { ref: refRegisterAtual, ...restRegisterAtual } = register("senha_atual");

  return (
    <Container maxWidth="sm" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Alterar Senha
      </Typography>
      <Box
        component="form"
        onSubmit={handleSubmit((v) => {
          setServerError(null);
          mutation.mutate(v);
        })}
      >
        <TextField
          label="Senha atual"
          type="password"
          fullWidth
          margin="normal"
          {...restRegisterAtual}
          inputRef={(el) => {
            refRegisterAtual(el);
            senhaAtualRef.current = el;
          }}
          error={Boolean(errors.senha_atual)}
          helperText={errors.senha_atual?.message ?? " "}
        />
        <TextField
          label="Nova senha"
          type="password"
          fullWidth
          margin="normal"
          {...register("nova_senha")}
          error={Boolean(errors.nova_senha)}
          helperText={errors.nova_senha?.message ?? " "}
        />
        <Box mt={1} mb={1}>
          <LinearProgress variant="determinate" value={forca.value} color={forca.color} />
          <Typography variant="caption" color={forca.color}>
            {forca.label}
          </Typography>
        </Box>
        <TextField
          label="Confirmar nova senha"
          type="password"
          fullWidth
          margin="normal"
          {...register("confirmar_senha")}
          error={Boolean(errors.confirmar_senha)}
          helperText={errors.confirmar_senha?.message ?? " "}
        />
        {serverError && (
          <Alert severity="error" role="alert" sx={{ mt: 2 }}>
            {serverError}
          </Alert>
        )}
        <Stack direction="row" spacing={2} mt={3}>
          <Button onClick={() => navigate("/cadastro")}>Cancelar</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={!isValid || isSubmitting || mutation.isPending || success}
          >
            {mutation.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </Stack>
      </Box>
      <Snackbar open={success} autoHideDuration={3000} onClose={() => setSuccess(false)}>
        <Alert severity="success" role="status">
          Senha alterada com sucesso.
        </Alert>
      </Snackbar>
    </Container>
  );
}
