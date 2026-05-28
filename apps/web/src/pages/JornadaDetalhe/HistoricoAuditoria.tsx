import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stack,
  Box,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import dayjs from "dayjs";
import { getAuditoria, auditoriaKeys } from "@/api/auditoria";

interface Props {
  jornadaId: string;
}

export function HistoricoAuditoria({ jornadaId }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: auditoriaKeys.list("Jornada", jornadaId),
    queryFn: () => getAuditoria("Jornada", jornadaId),
    enabled: expanded,
  });

  return (
    <Accordion expanded={expanded} onChange={(_e, v) => setExpanded(v)}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />} aria-controls="audit-content">
        <Typography>Histórico de auditoria</Typography>
      </AccordionSummary>
      <AccordionDetails>
        {isLoading && <Typography>Carregando...</Typography>}
        {data && data.length === 0 && (
          <Typography color="text.secondary">Nenhum registro.</Typography>
        )}
        <Stack spacing={1}>
          {data?.map((log) => (
            <Box key={log.id} p={1} border={1} borderColor="divider" borderRadius={1}>
              <Typography variant="caption">
                {dayjs(log.criado_em).format("DD/MM/YYYY HH:mm")} — {log.autor}
              </Typography>
              <Typography>Motivo: {log.motivo ?? "—"}</Typography>
              <Box
                mt={1}
                component="pre"
                sx={{
                  fontSize: 12,
                  bgcolor: "grey.100",
                  p: 1,
                  borderRadius: 1,
                  whiteSpace: "pre-wrap",
                }}
              >
                Antes: {log.antes_json ?? "—"}
                {"\n"}Depois: {log.depois_json}
              </Box>
            </Box>
          ))}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}
