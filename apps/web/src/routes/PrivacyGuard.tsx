import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { CircularProgress, Box } from "@mui/material";
import api from "@/api/client";
import type { PrivacyStatus } from "@/types/contracts";

export const privacyKeys = {
  status: ["privacidade", "status"] as const,
};

export function PrivacyGuard() {
  const location = useLocation();
  const { data, isLoading } = useQuery({
    queryKey: privacyKeys.status,
    queryFn: async (): Promise<PrivacyStatus> => {
      const r = await api.get<PrivacyStatus>("/api/v1/privacidade");
      return r.data;
    },
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  const isPrivacyRoute = location.pathname === "/privacidade";
  if (data?.accepted && isPrivacyRoute) {
    return <Navigate to="/jornadas" replace />;
  }
  if (!data?.accepted && !isPrivacyRoute) {
    return <Navigate to="/privacidade" replace />;
  }
  return <Outlet />;
}
