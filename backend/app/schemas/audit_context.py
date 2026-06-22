from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuditContext:
    usuario: str
    ip_origem: str
    criado_em: datetime
    nome_usuario: str | None = None
    hostname_origem: str | None = None
    user_agent: str | None = None

    def __post_init__(self) -> None:
        if not self.usuario.strip():
            raise ValueError("usuario é obrigatório.")
        if not self.ip_origem.strip():
            raise ValueError("ip_origem é obrigatório.")

    def to_record(self) -> dict[str, object]:
        return asdict(self)

