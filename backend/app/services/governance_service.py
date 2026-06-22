from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from backend.app.core.contracts import LOG_ALTERACOES_PATH


DECISION_COLUMNS = [
    "id_alteracao",
    "data_hora",
    "usuario",
    "perfil",
    "ip",
    "pc",
    "chave_registro",
    "acao",
    "campo_alterado",
    "valor_original",
    "valor_novo",
    "justificativa",
    "status",
    "validado",
    "status_validacao",
    "motivo_status",
]


class GovernanceService:
    """Registra decisões de validação no log de alterações.

    A aplicação não reescreve o mart grande a cada clique. Cada decisão entra
    em `log_alteracoes.parquet`; depois `gerar_oms_corrigido` materializa o
    estado mais recente em `agrupamento_oms_UNION_corrigido.parquet`.
    """

    def validar_registro(
        self,
        chave_registro: str,
        usuario: str,
        perfil: str,
        justificativa: str,
        ip: str | None = None,
        pc: str | None = None,
    ) -> dict[str, Any]:
        return self._registrar_decisao(
            chave_registro=chave_registro,
            usuario=usuario,
            perfil=perfil,
            ip=ip,
            pc=pc,
            acao="validar",
            status="aplicado",
            validado=True,
            status_validacao="validado",
            motivo_status=justificativa,
            justificativa=justificativa,
        )

    def rejeitar_registro(
        self,
        chave_registro: str,
        usuario: str,
        perfil: str,
        justificativa: str,
        ip: str | None = None,
        pc: str | None = None,
    ) -> dict[str, Any]:
        return self._registrar_decisao(
            chave_registro=chave_registro,
            usuario=usuario,
            perfil=perfil,
            ip=ip,
            pc=pc,
            acao="rejeitar",
            status="aplicado",
            validado=False,
            status_validacao="rejeitado",
            motivo_status=justificativa,
            justificativa=justificativa,
        )

    def ignorar_regra(
        self,
        chave_registro: str,
        usuario: str,
        perfil: str,
        justificativa: str,
        ip: str | None = None,
        pc: str | None = None,
    ) -> dict[str, Any]:
        return self._registrar_decisao(
            chave_registro=chave_registro,
            usuario=usuario,
            perfil=perfil,
            ip=ip,
            pc=pc,
            acao="ignorar_regra",
            status="aplicado",
            validado=False,
            status_validacao="ignorado",
            motivo_status=justificativa,
            justificativa=justificativa,
        )

    def aprovar_alteracao(
        self,
        id_alteracao: str,
        usuario: str,
        perfil: str,
        justificativa: str,
        ip: str | None = None,
        pc: str | None = None,
    ) -> dict[str, Any]:
        return self._registrar_decisao(
            chave_registro=id_alteracao,
            usuario=usuario,
            perfil=perfil,
            ip=ip,
            pc=pc,
            acao="aprovar_alteracao",
            status="aprovado",
            validado=False,
            status_validacao="em_analise",
            motivo_status=justificativa,
            justificativa=justificativa,
        )

    def rejeitar_alteracao(
        self,
        id_alteracao: str,
        usuario: str,
        perfil: str,
        justificativa: str,
        ip: str | None = None,
        pc: str | None = None,
    ) -> dict[str, Any]:
        return self._registrar_decisao(
            chave_registro=id_alteracao,
            usuario=usuario,
            perfil=perfil,
            ip=ip,
            pc=pc,
            acao="rejeitar_alteracao",
            status="rejeitado",
            validado=False,
            status_validacao="em_analise",
            motivo_status=justificativa,
            justificativa=justificativa,
        )

    def _registrar_decisao(
        self,
        *,
        chave_registro: str,
        usuario: str,
        perfil: str,
        ip: str | None,
        pc: str | None,
        acao: str,
        status: str,
        validado: bool,
        status_validacao: str,
        motivo_status: str,
        justificativa: str,
    ) -> dict[str, Any]:
        registro = {
            "id_alteracao": str(uuid4()),
            "data_hora": datetime.now().isoformat(timespec="seconds"),
            "usuario": usuario,
            "perfil": perfil,
            "ip": ip or "",
            "pc": pc or "",
            "chave_registro": chave_registro,
            "acao": acao,
            "campo_alterado": "status_validacao",
            "valor_original": "",
            "valor_novo": status_validacao,
            "justificativa": justificativa,
            "status": status,
            "validado": validado,
            "status_validacao": status_validacao,
            "motivo_status": motivo_status,
        }
        self._append_log(registro)
        return registro

    def _append_log(self, registro: dict[str, Any]) -> None:
        LOG_ALTERACOES_PATH.parent.mkdir(parents=True, exist_ok=True)
        new_row = pd.DataFrame([registro])
        if LOG_ALTERACOES_PATH.exists():
            existing = pd.read_parquet(LOG_ALTERACOES_PATH)
            for column in DECISION_COLUMNS:
                if column not in existing.columns:
                    existing[column] = None
            for column in existing.columns:
                if column not in new_row.columns:
                    new_row[column] = None
            output = pd.concat([existing, new_row[existing.columns]], ignore_index=True)
        else:
            output = new_row[DECISION_COLUMNS]

        tmp_path = Path(str(LOG_ALTERACOES_PATH) + ".tmp")
        output.to_parquet(tmp_path, index=False)
        tmp_path.replace(LOG_ALTERACOES_PATH)
