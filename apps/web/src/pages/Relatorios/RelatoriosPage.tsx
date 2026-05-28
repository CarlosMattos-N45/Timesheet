import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import dayjs, { type Dayjs } from "dayjs";
import {
  Container,
  Typography,
  Box,
  Button,
  Stack,
  Chip,
  Alert,
  Snackbar,
  Skeleton,
  Tooltip,
} from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { DatePicker, LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import {
  getRelatorioMeta,
  getRelatorioHistorico,
  urlDownloadRelatorio,
  relatoriosKeys,
} from "@/api/relatorios";
import api from "@/api/client";
import { terceirosKeys, getTerceiroMe } from "@/api/terceiros";
import { EnviarRelatorioDialog } from "@/components/EnviarRelatorioDialog";
import { formatDataHoraBR } from "@/lib/format/horario";
import type { HistoricoEnvioItem } from "@/types/contracts";

export function RelatoriosPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [mesSel, setMesSel] = useState<Dayjs>(() => dayjs().subtract(1, "month"));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    msg: string;
    severity: "success" | "error" | "info";
  } | null>(null);

  const mes = mesSel.format("YYYY-MM");

  const {
    data: meta,
    isLoading: loadingMeta,
    isError: errMeta,
  } = useQuery({
    queryKey: relatoriosKeys.meta(mes),
    queryFn: () => getRelatorioMeta(mes),
    retry: false,
  });

  const { data: historico = [] } = useQuery({
    queryKey: relatoriosKeys.historico(mes),
    queryFn: () => getRelatorioHistorico(mes),
  });

  const { data: terceiro } = useQuery({
    queryKey: terceirosKeys.me,
    queryFn: getTerceiroMe,
  });

  const regenerar = useMutation({
    mutationFn: async () => api.get(urlDownloadRelatorio(mes), { responseType: "blob" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: relatoriosKeys.meta(mes) });
      setSnackbar({ msg: "Relatório regenerado.", severity: "success" });
    },
    onError: () => setSnackbar({ msg: "Falha ao regenerar relatório.", severity: "error" }),
  });

  function baixarPdf() {
    const a = document.createElement("a");
    a.href = urlDownloadRelatorio(mes);
    a.target = "_self";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  const semDados = errMeta;

  const histColunas: GridColDef<HistoricoEnvioItem>[] = [
    {
      field: "enviado_em",
      headerName: "Quando",
      width: 170,
      valueFormatter: (v: string) => formatDataHoraBR(v),
    },
    { field: "email_destinatario", headerName: "Destinatário", flex: 1 },
    {
      field: "status",
      headerName: "Status",
      width: 110,
      renderCell: (p) => (
        <Chip
          label={p.row.status}
          color={p.row.status === "SUCESSO" ? "success" : "error"}
          size="small"
        />
      ),
    },
    {
      field: "erro_mensagem",
      headerName: "Erro",
      flex: 1,
      renderCell: (p) =>
        p.row.erro_mensagem ? (
          <Tooltip title={p.row.erro_mensagem}>
            <Typography variant="body2" noWrap>
              {p.row.erro_mensagem.slice(0, 60)}
            </Typography>
          </Tooltip>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <Container maxWidth="lg" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Relatórios
      </Typography>

      <Stack direction="row" spacing={2} alignItems="center" mb={2}>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <DatePicker
            views={["year", "month"]}
            label="Mês"
            value={mesSel}
            onChange={(v) => v && setMesSel(v)}
            maxDate={dayjs().subtract(1, "month")}
          />
        </LocalizationProvider>
      </Stack>

      {semDados ? (
        <Alert severity="info" sx={{ mt: 2 }}>
          Nenhuma jornada registrada para este mês. Não é possível gerar o relatório.
        </Alert>
      ) : (
        <>
          {meta?.invalidado_em && (
            <Alert
              severity="warning"
              sx={{ mb: 2 }}
              action={
                <Button
                  color="inherit"
                  size="small"
                  disabled={regenerar.isPending}
                  onClick={() => regenerar.mutate()}
                >
                  Atualizar relatório
                </Button>
              }
            >
              PDF desatualizado — clique em &quot;Atualizar relatório&quot; para regenerar.
            </Alert>
          )}

          <Box mb={2}>
            {loadingMeta ? (
              <Skeleton variant="rectangular" height={500} />
            ) : (
              <iframe
                title={`Relatório ${mes}`}
                src={urlDownloadRelatorio(mes)}
                style={{ width: "100%", height: 500, border: "1px solid #ccc" }}
              />
            )}
          </Box>

          <Stack direction="row" spacing={1} mb={2}>
            <Button variant="outlined" onClick={baixarPdf}>
              Baixar PDF
            </Button>
            <Button variant="contained" onClick={() => setDialogOpen(true)}>
              Enviar agora
            </Button>
            <Button onClick={() => navigate("/configuracoes/smtp")}>Configurar SMTP</Button>
          </Stack>

          <Typography variant="h6">Histórico de envios</Typography>
          <DataGrid<HistoricoEnvioItem>
            rows={historico}
            columns={histColunas}
            getRowId={(r) => r.id}
            autoHeight
            density="compact"
            pageSizeOptions={[10, 25]}
            initialState={{ pagination: { paginationModel: { pageSize: 10, page: 0 } } }}
          />
        </>
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
          role={snackbar?.severity === "error" ? "alert" : "status"}
        >
          {snackbar?.msg}
        </Alert>
      </Snackbar>
    </Container>
  );
}
