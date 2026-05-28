import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
} from "@mui/material";
import { postEnviarRelatorio } from "@/api/relatorios";
import { parseApiError } from "@/lib/errors";

interface Props {
  open: boolean;
  onClose: () => void;
  mes: string;
  emailDefault: string;
  onSuccess: (email: string) => void;
}

export function EnviarRelatorioDialog({ open, onClose, mes, emailDefault, onSuccess }: Props) {
  const [email, setEmail] = useState(emailDefault);
  const [erro, setErro] = useState<{ code: string; message: string } | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (open) {
      setEmail(emailDefault);
      setErro(null);
    }
  }, [open, emailDefault]);

  const mutation = useMutation({
    mutationFn: async () => postEnviarRelatorio(mes, email || undefined),
    onSuccess: () => onSuccess(email),
    onError: (err) => {
      const p = parseApiError(err);
      setErro({ code: p.code, message: p.message });
    },
  });

  const isSmtpMissing = erro?.code === "SMTP_NOT_CONFIGURED";

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Enviar relatório do mês {mes}</DialogTitle>
      <DialogContent>
        <TextField
          label="Destinatário"
          fullWidth
          margin="normal"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        {erro && (
          <Alert
            severity={isSmtpMissing ? "warning" : "error"}
            role="alert"
            action={
              isSmtpMissing ? (
                <Button
                  color="inherit"
                  size="small"
                  onClick={() => navigate("/configuracoes/smtp")}
                >
                  Configurar agora
                </Button>
              ) : undefined
            }
            sx={{ mt: 2 }}
          >
            {isSmtpMissing ? "SMTP não configurado." : erro.message}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancelar</Button>
        <Button
          variant="contained"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !email}
        >
          {mutation.isPending ? "Enviando..." : "Enviar"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
