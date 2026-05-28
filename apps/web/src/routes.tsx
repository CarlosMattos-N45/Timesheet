import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { PrivacyGuard } from "@/routes/PrivacyGuard";
import { AppLayout } from "@/components/AppLayout";
import { LoginPage } from "@/pages/Login/LoginPage";
import {
  JornadaDetalhePageStub,
  JornadaManualPageStub,
  RelatoriosPageStub,
  SmtpConfigPageStub,
} from "@/routes/PageStubs";
import { CadastroPage } from "@/pages/Cadastro/CadastroPage";
import { SenhaPage } from "@/pages/Cadastro/SenhaPage";
import { PrivacidadePage } from "@/pages/Privacidade/PrivacidadePage";
import { JornadasPage } from "@/pages/Jornadas/JornadasPage";

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
              { path: "/jornadas/manual", element: <JornadaManualPageStub /> },
              { path: "/jornadas/:id", element: <JornadaDetalhePageStub /> },
              { path: "/cadastro", element: <CadastroPage /> },
              { path: "/cadastro/senha", element: <SenhaPage /> },
              { path: "/relatorios", element: <RelatoriosPageStub /> },
              { path: "/configuracoes/smtp", element: <SmtpConfigPageStub /> },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/jornadas" replace /> },
]);
