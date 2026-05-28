import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItemButton,
  ListItemText,
  Box,
  Button,
  Divider,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import type { TerceiroResponse } from "@/types/contracts";
import { saudacaoAgora } from "@/lib/saudacao";

export const terceiroKeys = { me: ["terceiros", "me"] as const };

export function AppLayout({ children }: { children?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const { logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const { data: terceiro } = useQuery({
    queryKey: terceiroKeys.me,
    queryFn: async (): Promise<TerceiroResponse> => {
      const r = await api.get<TerceiroResponse>("/api/v1/terceiros/me");
      return r.data;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60_000,
  });

  const saud = saudacaoAgora();
  const nome = terceiro?.nome ?? "";

  return (
    <Box display="flex" flexDirection="column" minHeight="100vh">
      <AppBar position="static">
        <Toolbar>
          <IconButton
            edge="start"
            color="inherit"
            aria-label="abrir menu"
            onClick={() => setOpen(true)}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            TimeSheet Terceiros — {saud}
            {nome ? `, ${nome}` : ""}
          </Typography>
          <Button
            color="inherit"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sair
          </Button>
        </Toolbar>
      </AppBar>
      <Drawer open={open} onClose={() => setOpen(false)}>
        <Box sx={{ width: 280 }} role="navigation" aria-label="menu principal">
          <List>
            <ListItemButton
              selected={
                location.pathname.startsWith("/jornadas") &&
                location.pathname !== "/jornadas/manual"
              }
              onClick={() => {
                navigate("/jornadas");
                setOpen(false);
              }}
            >
              <ListItemText primary="Jornadas" />
            </ListItemButton>
            <ListItemButton
              selected={location.pathname === "/jornadas/manual"}
              onClick={() => {
                navigate("/jornadas/manual");
                setOpen(false);
              }}
            >
              <ListItemText primary="Nova jornada manual" />
            </ListItemButton>
            <Divider />
            <ListItemButton
              selected={location.pathname.startsWith("/relatorios")}
              onClick={() => {
                navigate("/relatorios");
                setOpen(false);
              }}
            >
              <ListItemText primary="Relatórios" />
            </ListItemButton>
            <ListItemButton
              selected={location.pathname.startsWith("/configuracoes/smtp")}
              onClick={() => {
                navigate("/configuracoes/smtp");
                setOpen(false);
              }}
            >
              <ListItemText primary="Configurar SMTP" />
            </ListItemButton>
            <Divider />
            <ListItemButton
              selected={location.pathname.startsWith("/cadastro")}
              onClick={() => {
                navigate("/cadastro");
                setOpen(false);
              }}
            >
              <ListItemText primary="Meu cadastro" />
            </ListItemButton>
          </List>
        </Box>
      </Drawer>
      <Box component="main" flexGrow={1} p={3}>
        {children ?? <Outlet />}
      </Box>
    </Box>
  );
}
