from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from backend.app.core.auth import AuthUser
from backend.app.core.contracts import LOG_ALTERACOES_PATH
from backend.app.repositories.parquet_log_repository import ParquetLogRepository
from backend.app.schemas.api_models import AlteracaoRequest
from backend.app.schemas.log_alteracoes import LOG_ALTERACOES_COLUMNS, LogAlteracao


class AlteracaoService:
    def __init__(self, log_path: Path = LOG_ALTERACOES_PATH) -> None:
        self.repository = ParquetLogRepository(
            path=log_path,
            columns=LOG_ALTERACOES_COLUMNS,
        )

    def solicitar(
        self,
        request: AlteracaoRequest,
        user: AuthUser,
        ip_origem: str,
        user_agent: str | None,
        hostname_origem: str | None = None,
    ) -> LogAlteracao:
        status = "aplicado" if user.perfil in {"admin", "gestor"} else "solicitado"
        record = LogAlteracao(
            id_alteracao=uuid4().hex,
            usuario=user.usuario,
            nome_usuario=user.nome_usuario,
            ip_origem=ip_origem,
            hostname_origem=hostname_origem,
            user_agent=user_agent,
            acao="solicitar_alteracao",
            anomes=request.anomes,
            chave_registro=request.chave_registro,
            campo=request.campo,
            valor_anterior=request.valor_anterior,
            valor_novo=request.valor_novo,
            justificativa=request.justificativa,
            criado_em=datetime.now(),
            status=status,  # type: ignore[arg-type]
        )
        self.repository.append([record.to_record()])
        return record

