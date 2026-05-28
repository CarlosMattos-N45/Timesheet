import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Container,
  Paper,
  Typography,
  Box,
  FormControlLabel,
  Checkbox,
  Button,
  Snackbar,
  Alert,
} from "@mui/material";
import { postAceitarPrivacidade, privacidadeKeys } from "@/api/privacidade";

const TEXTO_AVISO = `Dados coletados:
- Cadastro do Terceiro: nome, e-mail de contato, CNPJ da empresa.
- E-mail destinatário do relatório mensal (email_destinatario_relatorio): tratado como dado de terceiro fornecido pelo Terceiro.
- Marcações de jornada: horários de início, almoço e fim do trabalho.
- Atividades diárias e justificativas de ajustes manuais.

Finalidade:
- Automatizar e auditar o registro da jornada do Terceiro.
- Gerar e enviar relatório mensal por SMTP ao endereço informado.

Retenção:
- Marcações, jornadas, atividades: enquanto o Terceiro mantiver o sistema instalado.
- Relatórios PDF: 24 meses.
- Log de auditoria: indefinido nesta versão; revisão prevista em versões futuras.

Armazenamento:
- Todos os dados ficam em banco local SQLite com criptografia em repouso (SQLCipher).
- Credenciais do servidor SMTP são armazenadas criptografadas com AES-GCM no banco local.
- Nada é enviado para servidores externos exceto o relatório mensal por SMTP, sob seu controle.

Base legal:
- Execução de contrato e legítimo interesse (art. 7, II e IX da LGPD).

Contato DPO:
- O Terceiro é o controlador dos dados desta instalação. Para dúvidas, consultar a documentação ou o canal interno da Contratante.`;

export function PrivacidadePage() {
  const [aceito, setAceito] = useState(false);
  const [snackbar, setSnackbar] = useState<string | null>(null);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: postAceitarPrivacidade,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: privacidadeKeys.status });
    },
    onError: () => {
      setSnackbar("Não foi possível registrar o aceite. Tente novamente.");
    },
  });

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Aviso de Privacidade
        </Typography>
        <Box
          tabIndex={0}
          sx={{
            maxHeight: "50vh",
            overflowY: "auto",
            p: 2,
            border: 1,
            borderColor: "divider",
            borderRadius: 1,
            whiteSpace: "pre-wrap",
            fontFamily: "monospace",
            fontSize: 14,
          }}
        >
          {TEXTO_AVISO}
        </Box>
        <FormControlLabel
          sx={{ mt: 3 }}
          control={
            <Checkbox
              checked={aceito}
              onChange={(e) => setAceito(e.target.checked)}
              inputProps={{
                "aria-label": "Li e aceito os termos de privacidade",
                "aria-checked": aceito,
                role: "checkbox",
              }}
            />
          }
          label="Li e aceito os termos de privacidade"
        />
        <Box display="flex" justifyContent="flex-end" mt={2}>
          <Button
            variant="contained"
            disabled={!aceito || mutation.isPending}
            aria-busy={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Registrando..." : "Continuar"}
          </Button>
        </Box>
      </Paper>
      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={5000}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert severity="error" role="alert" onClose={() => setSnackbar(null)}>
          {snackbar}
        </Alert>
      </Snackbar>
    </Container>
  );
}
