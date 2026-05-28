import { useEffect, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
} from "@mui/material";

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: (motivo: string) => void;
  loading: boolean;
  error: string | null;
}

export function JustificativaDialog({ open, onClose, onConfirm, loading, error }: Props) {
  const [motivo, setMotivo] = useState("");
  useEffect(() => {
    if (open) setMotivo("");
  }, [open]);
  const ok = motivo.trim().length >= 5;
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Justificativa do ajuste</DialogTitle>
      <DialogContent>
        <TextField
          label="Motivo"
          multiline
          minRows={3}
          fullWidth
          margin="normal"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          helperText={`${motivo.length}/500` + (motivo.length < 5 ? " — Mínimo 5 caracteres" : "")}
          inputProps={{ maxLength: 500, "aria-label": "Motivo da alteração" }}
        />
        {error && (
          <Alert severity="error" role="alert">
            {error}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancelar</Button>
        <Button
          variant="contained"
          disabled={!ok || loading}
          onClick={() => onConfirm(motivo)}
        >
          {loading ? "Salvando..." : "Confirmar alterações"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
