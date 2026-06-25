from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FECHAMENTO_APURACAO_DIR = PROJECT_ROOT / "data" / "mart" / "apuracao" / "fechamento"
RAW_TEMP_DIR = PROJECT_ROOT / "data" / "raw_temp"


@dataclass(frozen=True)
class FechamentoTratamentoResult:
    anomes: str
    origem: Path
    parquet: Path
    parquet_atual: Path
    total_original: int
    removido_horario_negativo: int
    removido_sem_causa_componente: int
    total_final: int


class FechamentoTratamentoService:
    def gerar(self, anomes: str) -> FechamentoTratamentoResult:
        origem = FECHAMENTO_APURACAO_DIR / f"agrupamento_oms_FECHAMENTO_APURACAO_{anomes}.parquet"
        if not origem.exists():
            raise FileNotFoundError(
                f"Apuração de fechamento não encontrada: {origem}. "
                "Rode primeiro python -m backend.scripts.gerar_apuracao_fechamento."
            )

        FECHAMENTO_APURACAO_DIR.mkdir(parents=True, exist_ok=True)
        RAW_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        destino = FECHAMENTO_APURACAO_DIR / f"agrupamento_oms_FECHAMENTO_APURACAO_{anomes}_TRATADO.parquet"
        destino_atual = FECHAMENTO_APURACAO_DIR / "agrupamento_oms_FECHAMENTO_APURACAO_TRATADO_ATUAL.parquet"
        temp_path = RAW_TEMP_DIR / f"{destino.stem}.tmp.parquet"

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(
                """
                CREATE OR REPLACE TEMP VIEW base AS
                SELECT *
                FROM read_parquet(?)
                """,
                [str(origem)],
            )
            total_original = int(connection.execute("SELECT COUNT(*) FROM base").fetchone()[0])
            removido_horario_negativo = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM base
                    WHERE DATA_HORA_INIC_INTRP_TS IS NOT NULL
                      AND DATA_HORA_FIM_INTRP_TS IS NOT NULL
                      AND DATA_HORA_FIM_INTRP_TS < DATA_HORA_INIC_INTRP_TS
                    """
                ).fetchone()[0]
            )
            removido_sem_causa_componente = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM base
                    WHERE NOT (
                        DATA_HORA_INIC_INTRP_TS IS NOT NULL
                        AND DATA_HORA_FIM_INTRP_TS IS NOT NULL
                        AND DATA_HORA_FIM_INTRP_TS < DATA_HORA_INIC_INTRP_TS
                    )
                    AND (
                        NULLIF(TRIM(CAST(COD_CAUSA_INTRP AS VARCHAR)), '') IS NULL
                        OR NULLIF(TRIM(CAST(COD_COMP_INTRP AS VARCHAR)), '') IS NULL
                    )
                    """
                ).fetchone()[0]
            )

            if temp_path.exists():
                temp_path.unlink()
            connection.execute(
                """
                COPY (
                    SELECT *
                    FROM base
                    WHERE NOT (
                        DATA_HORA_INIC_INTRP_TS IS NOT NULL
                        AND DATA_HORA_FIM_INTRP_TS IS NOT NULL
                        AND DATA_HORA_FIM_INTRP_TS < DATA_HORA_INIC_INTRP_TS
                    )
                    AND NULLIF(TRIM(CAST(COD_CAUSA_INTRP AS VARCHAR)), '') IS NOT NULL
                    AND NULLIF(TRIM(CAST(COD_COMP_INTRP AS VARCHAR)), '') IS NOT NULL
                )
                TO ? (
                    FORMAT PARQUET,
                    COMPRESSION ZSTD
                )
                """,
                [str(temp_path)],
            )
            total_final = int(
                connection.execute(
                    "SELECT COUNT(*) FROM read_parquet(?)",
                    [str(temp_path)],
                ).fetchone()[0]
            )

        os.replace(temp_path, destino)
        _copiar_parquet(destino, destino_atual)

        return FechamentoTratamentoResult(
            anomes=anomes,
            origem=origem,
            parquet=destino,
            parquet_atual=destino_atual,
            total_original=total_original,
            removido_horario_negativo=removido_horario_negativo,
            removido_sem_causa_componente=removido_sem_causa_componente,
            total_final=total_final,
        )


def _copiar_parquet(origem: Path, destino: Path) -> None:
    with duckdb.connect(database=":memory:") as connection:
        connection.execute(
            "COPY (SELECT * FROM read_parquet(?)) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
            [str(origem), str(destino)],
        )
