import React, { useState, useMemo } from "react";
import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import dayjs, { type Dayjs } from "dayjs";
import utc from "dayjs/plugin/utc";
import {
  Container,
  Breadcrumbs,
  Link,
  Typography,
  Box,
  Chip,
  Stack,
  Button,
  TextField,
  Snackbar,
  Alert,
} from "@mui/material";
import {
  getJornadaDetalhe,
  putAjusteJornada,
  postAtividade,
  jornadasKeys,
} from "@/api/jornadas";
import { auditoriaKeys } from "@/api/auditoria";
import { formatTotal, calculaTotalDiario } from "@/lib/format/horario";
import { parseApiError } from "@/lib/errors";
import { JustificativaDialog } from "./JustificativaDialog";
import { HistoricoAuditoria } from "./HistoricoAuditoria";
import type {
  TipoMarcacao,
  StatusJornada,
} from "@/types/contracts";

dayjs.extend(utc);

const STATUS_COLOR: Record<StatusJornada, "default" | "success" | "warning" | "error"> = {
  EM_ANDAMENTO: "default",
  FECHADA: "success",
  AJUSTADA_MANUALMENTE: "warning",
  PENDENTE: "error",
};

const TIPO_LABEL: Record<TipoMarcacao, string> = {
  INICIO_JORNADA: "Horário de início",
  SAIDA_ALMOCO: "Horário de saída do almoço",
  RETORNO_ALMOCO: "Horário de retorno do almoço",
  FIM_JORNADA: "Horário de fim",
};

const TIPOS_ORDEM: TipoMarcacao[] = [
  "INICIO_JORNADA",
  "SAIDA_ALMOCO",
  "RETORNO_ALMOCO",
  "FIM_JORNADA",
];

type HorariosMap = Record<TipoMarcacao, Dayjs | null>;

const HORARIOS_VAZIOS: HorariosMap = {
  INICIO_JORNADA: null,
  SAIDA_ALMOCO: null,
  RETORNO_ALMOCO: null,
  FIM_JORNADA: null,
};

/** Converte Dayjs para string "HH:mm" local (BRT) para o input type=time */
function dayjsToTimeInput(d: Dayjs | null): string {
  if (!d || !d.isValid()) return "";
  return d.format("HH:mm");
}

/** Converte string "HH:mm" + data base para Dayjs UTC */
function timeInputToDayjs(timeStr: string, baseDate: string): Dayjs | null {
  const match = timeStr.match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return null;
  const parsed = dayjs(baseDate)
    .hour(Number(match[1]))
    .minute(Number(match[2]))
    .second(0)
    .millisecond(0);
  return parsed.isValid() ? parsed : null;
}

export function JornadaDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [editado, setEditado] = useState<HorariosMap>({ ...HORARIOS_VAZIOS });
  const [horariosInicializados, setHorariosInicializados] = useState(false);
  const [atividadeTxt, setAtividadeTxt] = useState("");
  const [atividadeDirty, setAtividadeDirty] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    msg: string;
    severity: "success" | "error";
  } | null>(null);

  const { data: jornada, isLoading, error: queryError } = useQuery({
    queryKey: jornadasKeys.detalhe(id!),
    queryFn: () => getJornadaDetalhe(id!),
    enabled: Boolean(id),
  });

  // Inicializar estado local com dados do fetch (somente uma vez)
  useMemo(() => {
    if (jornada && !horariosInicializados) {
      const map: HorariosMap = { ...HORARIOS_VAZIOS };
      for (const m of jornada.marcacoes) {
        const h = m.horario_efetivo ?? m.horario_registrado;
        map[m.tipo as TipoMarcacao] = dayjs(h);
      }
      setEditado(map);
      setAtividadeTxt(jornada.atividade?.descricao ?? "");
      setHorariosInicializados(true);
    }
  }, [jornada, horariosInicializados]);

  const editavel =
    jornada != null &&
    (jornada.status === "FECHADA" || jornada.status === "AJUSTADA_MANUALMENTE");

  const atividadeEditavel =
    jornada != null && jornada.status !== "EM_ANDAMENTO";

  const marcacoesAlteradas = useMemo<
    { tipo: TipoMarcacao; horario_efetivo: string }[]
  >(() => {
    if (!jornada) return [];
    const alts: { tipo: TipoMarcacao; horario_efetivo: string }[] = [];
    for (const m of jornada.marcacoes) {
      const tipo = m.tipo as TipoMarcacao;
      const original = dayjs(m.horario_efetivo ?? m.horario_registrado);
      const atual = editado[tipo];
      if (atual && atual.isValid() && !atual.isSame(original, "minute")) {
        alts.push({ tipo, horario_efetivo: atual.utc().toISOString() });
      }
    }
    return alts;
  }, [jornada, editado]);

  const isDirty = marcacoesAlteradas.length > 0;

  const totalAtual = useMemo(() => {
    return calculaTotalDiario(
      editado.INICIO_JORNADA?.isValid() ? editado.INICIO_JORNADA.toISOString() : null,
      editado.SAIDA_ALMOCO?.isValid() ? editado.SAIDA_ALMOCO.toISOString() : null,
      editado.RETORNO_ALMOCO?.isValid() ? editado.RETORNO_ALMOCO.toISOString() : null,
      editado.FIM_JORNADA?.isValid() ? editado.FIM_JORNADA.toISOString() : null
    );
  }, [editado]);

  const mutationAjuste = useMutation({
    mutationFn: (motivo: string) =>
      putAjusteJornada(id!, { marcacoes: marcacoesAlteradas, motivo }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: jornadasKeys.detalhe(id!) });
      void qc.invalidateQueries({ queryKey: jornadasKeys.all });
      void qc.invalidateQueries({ queryKey: auditoriaKeys.list("Jornada", id!) });
      setDialogOpen(false);
      setHorariosInicializados(false);
      setSnackbar({ msg: "Jornada atualizada com sucesso.", severity: "success" });
    },
  });

  const mutationAtividade = useMutation({
    mutationFn: () => postAtividade(id!, { descricao: atividadeTxt }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: jornadasKeys.detalhe(id!) });
      void qc.invalidateQueries({ queryKey: auditoriaKeys.list("Atividade", id!) });
      setAtividadeDirty(false);
      setSnackbar({ msg: "Atividade atualizada.", severity: "success" });
    },
    onError: (e) => {
      const p = parseApiError(e);
      setSnackbar({ msg: p.message, severity: "error" });
    },
  });

  if (queryError) {
    const status = (queryError as { response?: { status?: number } })?.response?.status;
    if (status === 404) {
      navigate("/jornadas");
      return null;
    }
  }

  if (isLoading || !jornada) {
    return <Container sx={{ mt: 3 }}>Carregando...</Container>;
  }

  const handleTimeChange = (tipo: TipoMarcacao, value: string) => {
    const parsed = timeInputToDayjs(value, jornada.data);
    if (parsed) {
      setEditado((prev) => ({ ...prev, [tipo]: parsed }));
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 2 }}>
      <Breadcrumbs>
        <Link component={RouterLink} to="/jornadas">
          Jornadas
        </Link>
        <Typography color="text.primary">
          {dayjs(jornada.data).format("DD/MM/YYYY")}
        </Typography>
      </Breadcrumbs>

      <Box display="flex" alignItems="center" gap={2} mt={2}>
        <Chip
          label={jornada.status}
          color={STATUS_COLOR[jornada.status]}
          role="status"
          aria-label={`Status: ${jornada.status}`}
        />
      </Box>

      {jornada.status === "PENDENTE" && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Esta jornada possui marcações pendentes. Ajuste os horários sinalizados.
        </Alert>
      )}

      <Stack direction="row" spacing={2} mt={3} flexWrap="wrap">
        {TIPOS_ORDEM.map((tipo) => {
          const marc = jornada.marcacoes.find((m) => m.tipo === tipo);
          const pendente = marc?.status === "PENDENTE";
          return (
            <TextField
              key={tipo}
              label={TIPO_LABEL[tipo]}
              type="time"
              value={dayjsToTimeInput(editado[tipo])}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                handleTimeChange(tipo, e.target.value)
              }
              disabled={!editavel}
              error={pendente}
              helperText={pendente ? "Marcação pendente — ajuste" : undefined}
              InputLabelProps={{ shrink: true }}
              inputProps={{
                "aria-label": TIPO_LABEL[tipo],
                step: 60,
              }}
              sx={
                pendente
                  ? { "& .MuiOutlinedInput-root": { borderColor: "warning.main" } }
                  : undefined
              }
            />
          );
        })}
      </Stack>

      <Box mt={2}>
        <Typography variant="body1">
          {`Total: ${formatTotal(totalAtual)}`}
        </Typography>
      </Box>

      <Box mt={3}>
        <TextField
          label="Atividade do dia"
          multiline
          minRows={3}
          fullWidth
          value={atividadeTxt}
          disabled={!atividadeEditavel}
          onChange={(e) => {
            setAtividadeTxt(e.target.value);
            setAtividadeDirty(true);
          }}
          helperText={
            `${atividadeTxt.length}/2000` +
            (atividadeTxt.length < 10 ? " — Mínimo 10 caracteres" : "")
          }
          error={atividadeDirty && atividadeTxt.length < 10}
          inputProps={{ "aria-label": "Atividade do dia" }}
        />
        <Box mt={1}>
          <Button
            variant="outlined"
            disabled={
              !atividadeDirty ||
              atividadeTxt.length < 10 ||
              mutationAtividade.isPending
            }
            onClick={() => mutationAtividade.mutate()}
          >
            Salvar atividade
          </Button>
        </Box>
      </Box>

      {isDirty && (
        <Box mt={3}>
          <Button variant="contained" onClick={() => setDialogOpen(true)}>
            Salvar alterações
          </Button>
        </Box>
      )}

      <Box mt={4}>
        <Typography variant="h6" gutterBottom>
          Justificativas anteriores
        </Typography>
        {jornada.justificativas.length === 0 ? (
          <Typography color="text.secondary">Nenhuma.</Typography>
        ) : (
          <Stack spacing={1}>
            {jornada.justificativas.map((j) => (
              <Box
                key={j.id}
                p={1}
                border={1}
                borderColor="divider"
                borderRadius={1}
              >
                <Typography variant="caption">
                  {dayjs(j.criada_em).format("DD/MM/YYYY HH:mm")} —{" "}
                  {j.usuario_responsavel}
                </Typography>
                <Typography>{j.motivo}</Typography>
              </Box>
            ))}
          </Stack>
        )}
      </Box>

      <Box mt={4}>
        <HistoricoAuditoria jornadaId={jornada.id} />
      </Box>

      <JustificativaDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onConfirm={(motivo) => mutationAjuste.mutate(motivo)}
        loading={mutationAjuste.isPending}
        error={
          mutationAjuste.error
            ? parseApiError(mutationAjuste.error).message
            : null
        }
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
