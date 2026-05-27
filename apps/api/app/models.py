"""Re-export of all ORM models. Importing this module registers every table
on ``Base.metadata`` for Alembic autogenerate and ``Base.metadata.create_all``.
"""

from app.modules.atividades.model import Atividade
from app.modules.auditoria.model import LogAuditoria
from app.modules.auth.model import RefreshToken
from app.modules.jornadas.model import Jornada
from app.modules.justificativas.model import Justificativa
from app.modules.marcacoes.model import Marcacao
from app.modules.privacidade.model import PrivacyAcceptance
from app.modules.relatorios.model import HistoricoEnvioRelatorio, RelatorioGerado
from app.modules.smtp.model import SmtpConfig
from app.modules.terceiros.model import Terceiro

__all__ = [
    "Atividade",
    "HistoricoEnvioRelatorio",
    "Jornada",
    "Justificativa",
    "LogAuditoria",
    "Marcacao",
    "PrivacyAcceptance",
    "RefreshToken",
    "RelatorioGerado",
    "SmtpConfig",
    "Terceiro",
]
