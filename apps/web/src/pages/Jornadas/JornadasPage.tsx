import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import dayjs, { type Dayjs } from "dayjs";
import {
  Container,
  Typography,
  Box,
  Button,
  Stack,
  Chip,
  Tooltip,
  Snackbar,
  Alert,
} from "@mui/material";
import WarningIcon from "@mui/icons-material/Warning";
import { DataGrid, type GridColDef, type GridRenderCellParams } from "@mui/x-data-grid";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { getJornadasMes, jornadasKeys } from "@/api/jornadas";
import { urlDownloadRelatorio } from "@/api/relatorios";
import { terceirosKeys, getTerceiroMe } from "@/api/terceiros";
import type { JornadaResumo } from "@/types/contracts";
import { formatHoraBR, formatTotal, formatData, formatDiaSemana } from "@/lib/format/horario";
import { EnviarRelatorioDialog } from "./EnviarRelatorioDialog";

const STATUS_COLOR: Record<
  JornadaResumo["status"],
  "default" | "success" | "warning" | "error"
> = {
  EM_ANDAMENTO: "default",
  FECHADA: "success",
  AJUSTADA_MANUALMENTE: "warning",
  PENDENTE: "error",
};

export function JornadasPage() {
  const navigate = useNavigate();
  const [mesSel, setMesSel] = useState<Dayjs>(dayjs());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    msg: string;
    severity: "success" | "error";
  } | null>(null);

  const mes = mesSel.format("YYYY-MM");

  const { data, isLoading } = useQuery({
    queryKey: jornadasKeys.lista(mes),
    queryFn: () => getJornadasMes(mes),
  });

  const { data: terceiro } = useQuery({
    queryKey: terceirosKeys.me,
    queryFn: getTerceiroMe,
    staleTime: 5 * 60_000,
  });

  const vazio = !data || data.jornadas.length === 0;

  const colunas: GridColDef<JornadaResumo>[] = useMemo(
    () => [
      {
        field: "data",
        headerName: "Data",
        width: 90,
        valueFormatter: (v: string) => formatData(v),
      },
      {
        field: "diaSemana",
        headerName: "Dia",
        width: 70,
        valueGetter: (_v: unknown, row: JornadaResumo) => formatDiaSemana(row.data),
      },
      {
        field: "horario_inicio",
        headerName: "Início",
        width: 90,
        valueFormatter: (v: string | null) => formatHoraBR(v),
      },
      {
        field: "horario_saida_almoco",
        headerName: "Saída Almoço",
        width: 120,
        valueFormatter: (v: string | null) => formatHoraBR(v),
      },
      {
        field: "horario_retorno_almoco",
        headerName: "Retorno Almoço",
        width: 130,
        valueFormatter: (v: string | null) => formatHoraBR(v),
      },
      {
        field: "horario_fim",
        headerName: "Fim",
        width: 90,
        valueFormatter: (v: string | null) => formatHoraBR(v),
      },
      {
        field: "total_horas_apuradas_s",
        headerName: "Total",
        width: 90,
        valueFormatter: (v: number | null) => formatTotal(v),
      },
      {
        field: "status",
        headerName: "Status",
        width: 240,
        renderCell: (p: GridRenderCellParams<JornadaResumo>) => (
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip label={p.row.status} color={STATUS_COLOR[p.row.status]} size="small" />
            {p.row.tem_marcacao_pendente && (
              <Chip
                label="PENDENTE"
                color="error"
                size="small"
                icon={<WarningIcon />}
              />
            )}
          </Stack>
        ),
      },
    ],
    []
  );

  function baixarPdf() {
    const a = document.createElement("a");
    a.href = urlDownloadRelatorio(mes);
    a.target = "_self";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Jornadas
      </Typography>
      <Stack direction="row" spacing={2} alignItems="center" mb={2}>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <DatePicker
            views={["year", "month"]}
            label="Mês"
            value={mesSel}
            onChange={(v) => v && setMesSel(v)}
            maxDate={dayjs()}
          />
        </LocalizationProvider>
        <Typography variant="body1">
          Total no mês: <strong>{formatTotal(data?.total_horas_mes_s ?? null)}</strong>
        </Typography>
      </Stack>
      <Stack direction="row" spacing={1} mb={2}>
        <Button variant="contained" onClick={() => navigate("/jornadas/manual")}>
          Nova jornada manual
        </Button>
        <Tooltip title={vazio ? "Nenhuma jornada no mês" : ""}>
          <span>
            <Button variant="outlined" disabled={vazio} onClick={baixarPdf}>
              Baixar PDF
            </Button>
          </span>
        </Tooltip>
        <Tooltip title={vazio ? "Nenhuma jornada no mês" : ""}>
          <span>
            <Button variant="outlined" disabled={vazio} onClick={() => setDialogOpen(true)}>
              Enviar por e-mail
            </Button>
          </span>
        </Tooltip>
      </Stack>

      {vazio && !isLoading ? (
        <Box textAlign="center" py={6}>
          <Typography color="text.secondary" mb={2}>
            Nenhuma jornada registrada para este mês.
          </Typography>
          <Button variant="contained" onClick={() => navigate("/jornadas/manual")}>
            Criar jornada manual
          </Button>
        </Box>
      ) : (
        <DataGrid<JornadaResumo>
          rows={data?.jornadas ?? []}
          columns={colunas}
          loading={isLoading}
          getRowId={(r) => r.id}
          onRowClick={(p) => navigate(`/jornadas/${p.id}`)}
          autoHeight
          disableRowSelectionOnClick
          initialState={{ pagination: { paginationModel: { pageSize: 31, page: 0 } } }}
          pageSizeOptions={[31]}
        />
      )}

      <EnviarRelatorioDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        mes={mes}
        emailDefault={terceiro?.email_destinatario_relatorio ?? ""}
        onSuccess={(email) => {
          setDialogOpen(false);
          setSnackbar({ msg: `Relatório enviado para ${email}.`, severity: "success" });
        }}
      />

      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={5000}
        onClose={() => setSnackbar(null)}
      >
        <Alert
          severity={snackbar?.severity ?? "info"}
          onClose={() => setSnackbar(null)}
          role="status"
        >
          {snackbar?.msg}
        </Alert>
      </Snackbar>
    </Container>
  );
}
