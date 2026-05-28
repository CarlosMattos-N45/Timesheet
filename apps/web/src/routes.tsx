import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { PrivacyGuard } from "@/routes/PrivacyGuard";
import { AppLayout } from "@/components/AppLayout";
import { LoginPage } from "@/pages/Login/LoginPage";
import { JornadaManualPage } from "@/pages/JornadaManual/JornadaManualPage";
import { JornadaDetalhePage } from "@/pages/JornadaDetalhe/JornadaDetalhePage";
import { CadastroPage } from "@/pages/Cadastro/CadastroPage";
import { SenhaPage } from "@/pages/Cadastro/SenhaPage";
import { PrivacidadePage } from "@/pages/Privacidade/PrivacidadePage";
import { JornadasPage } from "@/pages/Jornadas/JornadasPage";
import { RelatoriosPage } from "@/pages/Relatorios/RelatoriosPage";
import { SmtpConfigPage } from "@/pages/Configuracoes/SmtpConfigPage";

export const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/jornadas" replace /> },
  { path: "/login", element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <PrivacyGuard />,
        children: [
          { path: "/privacidade", element: <PrivacidadePage /> },
          {
            element: <AppLayout />,
            children: [
              { path: "/jornadas", element: <JornadasPage /> },
              { path: "/jornadas/manual", element: <JornadaManualPage /> },
              { path: "/jornadas/:id", element: <JornadaDetalhePage /> },
              { path: "/cadastro", element: <CadastroPage /> },
              { path: "/cadastro/senha", element: <SenhaPage /> },
              { path: "/relatorios", element: <RelatoriosPage /> },
              { path: "/configuracoes/smtp", element: <SmtpConfigPage /> },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/jornadas" replace /> },
]);
