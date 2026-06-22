from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

from backend.app.core.contracts import MART_DIR, OMS_UNION_PARQUET_PATH, PARQUET_COMPRESSION


APURACAO_DIR = MART_DIR / "apuracao"
APURACAO_ATUAL_PATH = APURACAO_DIR / "agrupamento_oms_APURACAO_ATUAL.parquet"
APURACAO_CORRIGIDO_ATUAL_PATH = APURACAO_DIR / "agrupamento_oms_APURACAO_CORRIGIDO_ATUAL.parquet"


@dataclass(frozen=True)
class EtlApuracaoResult:
    anomes: str
    origem: str
    parquet: str
    parquet_atual: str
    linhas_saida: int
    remover_rejeitados: bool
    remover_canceladas: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EtlApuracaoService:
    def executar(
        self,
        anomes: str,
        remover_rejeitados: bool = False,
        remover_canceladas: bool = False,
    ) -> EtlApuracaoResult:
        anomes = self._normalizar_anomes(anomes)
        origem = self._origem_union()
        inicio, proximo_mes = self._janela_mes(anomes)

        APURACAO_DIR.mkdir(parents=True, exist_ok=True)
        destino = APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}.parquet"

        filtros = [
            f"inicio_ts >= TIMESTAMP '{inicio.isoformat()} 00:00:00'",
            f"inicio_ts < TIMESTAMP '{proximo_mes.isoformat()} 00:00:00'",
            f"fim_ts >= TIMESTAMP '{inicio.isoformat()} 00:00:00'",
            f"fim_ts < TIMESTAMP '{proximo_mes.isoformat()} 00:00:00'",
        ]

        if remover_rejeitados:
            filtros.append(
                "(status_validacao IS NULL OR lower(CAST(status_validacao AS VARCHAR)) <> 'rejeitado')"
            )

        if remover_canceladas:
            filtros.append("(ESTADO_INTRP IS NULL OR trim(CAST(ESTADO_INTRP AS VARCHAR)) <> '7')")

        where_sql = " AND ".join(filtros)

        query = f"""
            COPY (
                WITH base AS (
                    SELECT
                        *,
                        COALESCE(
                            TRY_CAST(DATA_HORA_INIC_INTRP AS TIMESTAMP),
                            TRY_STRPTIME(CAST(DATA_HORA_INIC_INTRP AS VARCHAR), '%d/%m/%Y %H:%M:%S')
                        ) AS inicio_ts,
                        COALESCE(
                            TRY_CAST(DATA_HORA_FIM_INTRP AS TIMESTAMP),
                            TRY_STRPTIME(CAST(DATA_HORA_FIM_INTRP AS VARCHAR), '%d/%m/%Y %H:%M:%S')
                        ) AS fim_ts
                    FROM read_parquet('{self._sql_literal(str(origem))}')
                )
                SELECT
                    * EXCLUDE (inicio_ts, fim_ts),
                    '{anomes}' AS MES_APURACAO,
                    CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS DATA_HORA_ETL_APURACAO
                FROM base
                WHERE {where_sql}
            )
            TO '{self._sql_literal(str(destino))}'
            (FORMAT PARQUET, COMPRESSION '{PARQUET_COMPRESSION}')
        """

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(query)
            linhas_saida = int(
                connection.execute(
                    "SELECT count(*) FROM read_parquet(?)",
                    [str(destino)],
                ).fetchone()[0]
            )

        shutil.copyfile(destino, APURACAO_ATUAL_PATH)
        if APURACAO_CORRIGIDO_ATUAL_PATH.exists():
            APURACAO_CORRIGIDO_ATUAL_PATH.unlink()

        try:
            from backend.app.services.apuracao_resumo_service import ApuracaoResumoService

            ApuracaoResumoService().materializar(anomes=anomes, origem=APURACAO_ATUAL_PATH)
        except Exception:
            pass

        return EtlApuracaoResult(
            anomes=anomes,
            origem=str(origem),
            parquet=str(destino),
            parquet_atual=str(APURACAO_ATUAL_PATH),
            linhas_saida=linhas_saida,
            remover_rejeitados=remover_rejeitados,
            remover_canceladas=remover_canceladas,
        )

    def _origem_union(self) -> Path:
        if not OMS_UNION_PARQUET_PATH.exists():
            raise FileNotFoundError(f"Mart UNION não encontrado: {OMS_UNION_PARQUET_PATH}")
        return OMS_UNION_PARQUET_PATH

    def _normalizar_anomes(self, anomes: str) -> str:
        value = str(anomes).strip()
        if len(value) != 6 or not value.isdigit():
            raise ValueError("Mês de apuração inválido. Use o formato AAAAMM, exemplo 202605.")
        return value

    def _janela_mes(self, anomes: str) -> tuple[date, date]:
        ano = int(anomes[:4])
        mes = int(anomes[4:])
        if mes < 1 or mes > 12:
            raise ValueError("Mês de apuração inválido.")
        inicio = date(ano, mes, 1)
        if mes == 12:
            return inicio, date(ano + 1, 1, 1)
        return inicio, date(ano, mes + 1, 1)

    def _sql_literal(self, value: str) -> str:
        return value.replace("'", "''")


EtlService = EtlApuracaoService
