from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal


StatusAlteracao = Literal[
    "solicitado",
    "aprovado",
    "rejeitado",
    "aplicado",
    "erro",
]


@dataclass(frozen=True)
class LogAlteracao:
    id_alteracao: str
    usuario: str
    nome_usuario: str | None
    ip_origem: str
    hostname_origem: str | None
    user_agent: str | None
    acao: str
    anomes: str
    chave_registro: str
    campo: str | None
    valor_anterior: str | None
    valor_novo: str | None
    justificativa: str | None
    criado_em: datetime
    status: StatusAlteracao

    def __post_init__(self) -> None:
        if not self.id_alteracao.strip():
            raise ValueError("id_alteracao é obrigatório.")
        if not self.usuario.strip():
            raise ValueError("usuario é obrigatório.")
        if not self.ip_origem.strip():
            raise ValueError("ip_origem é obrigatório.")
        if len(self.anomes) != 6 or not self.anomes.isdigit():
            raise ValueError("anomes deve estar no formato YYYYMM.")
        if not self.chave_registro.strip():
            raise ValueError("chave_registro é obrigatória.")

    def to_record(self) -> dict[str, object]:
        return asdict(self)


LOG_ALTERACOES_COLUMNS = [
    "id_alteracao",
    "usuario",
    "nome_usuario",
    "ip_origem",
    "hostname_origem",
    "user_agent",
    "acao",
    "anomes",
    "chave_registro",
    "campo",
    "valor_anterior",
    "valor_novo",
    "justificativa",
    "criado_em",
    "status",
]

