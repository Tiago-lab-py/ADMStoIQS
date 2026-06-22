from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal


StatusLeituraCsv = Literal["processado", "erro", "ignorado"]


@dataclass(frozen=True)
class LogLeituraCsv:
    arquivo_path: str
    arquivo_nome: str
    arquivo_tamanho_bytes: int
    arquivo_modificado_em: datetime
    arquivo_hash: str | None
    anomes: str
    processado_em: datetime
    status: StatusLeituraCsv
    linhas_lidas: int
    linhas_processadas: int
    mensagem_erro: str | None = None

    def __post_init__(self) -> None:
        if len(self.anomes) != 6 or not self.anomes.isdigit():
            raise ValueError("anomes deve estar no formato YYYYMM.")
        if self.arquivo_tamanho_bytes < 0:
            raise ValueError("arquivo_tamanho_bytes não pode ser negativo.")
        if self.linhas_lidas < 0:
            raise ValueError("linhas_lidas não pode ser negativo.")
        if self.linhas_processadas < 0:
            raise ValueError("linhas_processadas não pode ser negativo.")

    def to_record(self) -> dict[str, object]:
        return asdict(self)


LOG_LEITURA_CSV_COLUMNS = [
    "arquivo_path",
    "arquivo_nome",
    "arquivo_tamanho_bytes",
    "arquivo_modificado_em",
    "arquivo_hash",
    "anomes",
    "processado_em",
    "status",
    "linhas_lidas",
    "linhas_processadas",
    "mensagem_erro",
]

