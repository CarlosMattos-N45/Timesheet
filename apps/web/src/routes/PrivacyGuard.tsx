import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { CircularProgress, Box } from "@mui/material";
import { privacidadeKeys, getStatusPrivacidade } from "@/api/privacidade";

export function PrivacyGuard() {
  const location = useLocation();
  const { data, isLoading } = useQuery({
    queryKey: privacidadeKeys.status,
    queryFn: getStatusPrivacidade,
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
