import { Typography, Box } from "@mui/material";

function makeStub(label: string, taskId: string) {
  return function Stub() {
    return (
      <Box p={4}>
        <Typography variant="h5" component="h1">
          {label}
        </Typography>
        <Typography color="text.secondary">Em construção — {taskId}</Typography>
      </Box>
    );
  };
}

export const LoginPageStub = makeStub("Login", "TASK-021");
export const PrivacidadePageStub = makeStub("Privacidade", "TASK-022");
export const JornadasPageStub = makeStub("Jornadas", "TASK-023");
export const JornadaDetalhePageStub = makeStub("Detalhe da Jornada", "TASK-024");
export const JornadaManualPageStub = makeStub("Nova Jornada Manual", "TASK-025");
export const CadastroPageStub = makeStub("Cadastro", "TASK-026");
export const SenhaPageStub = makeStub("Alterar Senha", "TASK-026");
