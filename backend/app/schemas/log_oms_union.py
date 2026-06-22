from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal


StatusOmsUnion = Literal["inicio", "processando", "sucesso", "erro"]


@dataclass(frozen=True)
class LogOmsUnion:
    run_id: str
    etapa: str
    status: StatusOmsUnion
    mensagem: str
    arquivos_origem: int | None
    linhas_origem: int | None
    linhas_saida: int | None
    parquet_path: str | None
    criado_em: datetime

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id é obrigatório.")
        if not self.etapa.strip():
            raise ValueError("etapa é obrigatória.")
        if not self.status.strip():
            raise ValueError("status é obrigatório.")

    def to_record(self) -> dict[str, object]:
        return asdict(self)


LOG_OMS_UNION_COLUMNS = [
    "run_id",
    "etapa",
    "status",
    "mensagem",
    "arquivos_origem",
    "linhas_origem",
    "linhas_saida",
    "parquet_path",
    "criado_em",
]
