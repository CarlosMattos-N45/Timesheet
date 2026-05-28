import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  Link,
  Tooltip,
  Box,
} from "@mui/material";
import { useAuth } from "@/auth/AuthContext";
import { saudacaoAgora } from "@/lib/saudacao";
import { parseApiError } from "@/lib/errors";
import { loginSchema, type LoginFormValues } from "@/lib/schemas/login";

interface ErrorState {
  code: string;
  message: string;
}

const MENSAGENS: Record<string, string> = {
  UNAUTHORIZED: "E-mail ou senha inválidos. Verifique e tente novamente.",
  RATE_LIMITED: "Muitas tentativas. Aguarde alguns instantes e tente novamente.",
  NETWORK_ERROR: "Falha de conexão. Verifique o serviço local.",
};

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState<ErrorState | null>(null);
  const senhaRef = useRef<HTMLInputElement | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isSubmitting },
    resetField,
    setFocus,
  } = useForm<LoginFormValues>({
    mode: "onChange",
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", senha: "" },
  });

  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as { from?: string } | null)?.from ?? "/jornadas";
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, location.state, navigate]);

  async function onSubmit(values: LoginFormValues): Promise<void> {
    setServerError(null);
    try {
      await login(values.email, values.senha);
      navigate("/jornadas", { replace: true });
    } catch (err) {
      const parsed = parseApiError(err);
      setServerError({
        code: parsed.code,
        message: MENSAGENS[parsed.code] ?? parsed.message,
      });
      resetField("senha");
      setTimeout(() => setFocus("senha"), 0);
    }
  }

  const saud = saudacaoAgora();

  return (
    <Container maxWidth="xs" sx={{ mt: 8 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Login
        </Typography>
        <Typography variant="h5" component="p" color="text.secondary" mb={3}>
          {saud}.
        </Typography>
        <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <TextField
            label="E-mail"
            type="email"
            fullWidth
            margin="normal"
            error={Boolean(errors.email)}
            helperText={errors.email?.message ?? " "}
            inputProps={{ "aria-invalid": Boolean(errors.email) }}
            {...register("email")}
            autoFocus
          />
          <TextField
            label="Senha"
            type="password"
            fullWidth
            margin="normal"
            error={Boolean(errors.senha)}
            helperText={errors.senha?.message ?? " "}
            inputProps={{ "aria-invalid": Boolean(errors.senha) }}
            {...register("senha")}
            inputRef={senhaRef}
          />
          {serverError && (
            <Alert severity="error" role="alert" sx={{ mt: 2 }}>
              {serverError.message}
            </Alert>
          )}
          <Button
            type="submit"
            variant="contained"
            fullWidth
            size="large"
            sx={{ mt: 3, mb: 2 }}
            disabled={!isValid || isSubmitting}
            aria-busy={isSubmitting}
          >
            {isSubmitting ? "Entrando..." : "Entrar"}
          </Button>
          <Tooltip title="Recuperação de senha disponível em breve" describeChild>
            <span>
              <Link
                component="span"
                aria-disabled="true"
                sx={{
                  display: "block",
                  textAlign: "center",
                  color: "text.disabled",
                  cursor: "not-allowed",
                }}
              >
                Esqueci minha senha
              </Link>
            </span>
          </Tooltip>
        </Box>
      </Paper>
    </Container>
  );
}
