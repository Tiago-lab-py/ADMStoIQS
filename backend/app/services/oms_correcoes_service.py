from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from shutil import copyfile
from typing import Any

import duckdb

from backend.app.core.contracts import (
    LOG_ALTERACOES_PATH,
    MART_DIR,
    OMS_UNION_CORRIGIDO_LEGACY_PARQUET_PATH,
    OMS_UNION_CORRIGIDO_PARQUET_PATH,
    OMS_UNION_LEGACY_PARQUET_PATH,
    OMS_UNION_PARQUET_PATH,
)


APURACAO_DIR = MART_DIR / "apuracao"
APURACAO_ATUAL_PATH = APURACAO_DIR / "agrupamento_oms_APURACAO_ATUAL.parquet"
APURACAO_CORRIGIDO_ATUAL_PATH = APURACAO_DIR / "agrupamento_oms_APURACAO_CORRIGIDO_ATUAL.parquet"


@dataclass
class OmsCorrigidoResult:
    caminho: str
    linhas_saida: int
    alteracoes_aplicaveis: int

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


class OmsCorrecoesService:
    """Materializa a base corrigida com colunas de governança.

    A base corrigida parte sempre do mart `UNION`. O log de alterações define
    o último status de validação conhecido para cada chave.
    """

    def gerar_corrigido(self) -> OmsCorrigidoResult:
        source_path = self._source_path()
        output_path = self._output_path(source_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with duckdb.connect(database=":memory:") as connection:
            connection.execute("PRAGMA threads=4")
            if self._has_governance_log():
                self._write_with_governance_log(connection, source_path, output_path)
                alteracoes_aplicaveis = self._count_governance_rows(connection)
            else:
                self._write_without_log(connection, source_path, output_path)
                alteracoes_aplicaveis = 0

            linhas_saida = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(output_path)],
            ).fetchone()[0]

        self._refresh_aliases(source_path, output_path)
        return OmsCorrigidoResult(
            caminho=str(output_path),
            linhas_saida=linhas_saida,
            alteracoes_aplicaveis=alteracoes_aplicaveis,
        )

    def generate(self) -> OmsCorrigidoResult:
        return self.gerar_corrigido()

    def process(self) -> OmsCorrigidoResult:
        return self.gerar_corrigido()

    def __call__(self) -> OmsCorrigidoResult:
        return self.gerar_corrigido()

    def _source_path(self) -> Path:
        if APURACAO_ATUAL_PATH.exists():
            return APURACAO_ATUAL_PATH
        for path in (OMS_UNION_PARQUET_PATH, OMS_UNION_LEGACY_PARQUET_PATH):
            if path.exists():
                return path
        raise FileNotFoundError(
            "Mart UNION não encontrado. Gere com: "
            "python -m backend.scripts.gerar_oms_union"
        )

    def _output_path(self, source_path: Path) -> Path:
        if source_path == APURACAO_ATUAL_PATH:
            mes_apuracao = self._mes_apuracao(source_path)
            if mes_apuracao:
                return APURACAO_DIR / f"agrupamento_oms_APURACAO_{mes_apuracao}_corrigido.parquet"
            return APURACAO_CORRIGIDO_ATUAL_PATH
        return OMS_UNION_CORRIGIDO_PARQUET_PATH

    def _mes_apuracao(self, source_path: Path) -> str:
        try:
            with duckdb.connect(database=":memory:") as connection:
                row = connection.execute(
                    """
                    SELECT CAST(MES_APURACAO AS VARCHAR)
                    FROM read_parquet(?)
                    WHERE MES_APURACAO IS NOT NULL
                    LIMIT 1
                    """,
                    [str(source_path)],
                ).fetchone()
            return row[0] if row else ""
        except Exception:
            return ""

    def _has_governance_log(self) -> bool:
        return LOG_ALTERACOES_PATH.exists()

    def _write_without_log(
        self,
        connection: duckdb.DuckDBPyConnection,
        source_path: Path,
        output_path: Path,
    ) -> None:
        connection.execute(
            """
            COPY (
                SELECT
                    src.*,
                    false AS validado,
                    'pendente' AS status_validacao,
                    CAST(NULL AS VARCHAR) AS motivo_status,
                    CAST(NULL AS VARCHAR) AS usuario_validacao,
                    CAST(NULL AS TIMESTAMP) AS data_hora_validacao
                FROM read_parquet(?) AS src
            )
            TO ?
            (FORMAT PARQUET, COMPRESSION ZSTD)
            """,
            [str(source_path), str(output_path)],
        )

    def _write_with_governance_log(
        self,
        connection: duckdb.DuckDBPyConnection,
        source_path: Path,
        output_path: Path,
    ) -> None:
        connection.execute(
            """
            CREATE TEMP TABLE log_raw AS
            SELECT *
            FROM read_parquet(?)
            """,
            [str(LOG_ALTERACOES_PATH)],
        )

        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info('log_raw')").fetchall()
        }

        if "chave_registro" not in columns:
            self._write_without_log(connection, source_path, output_path)
            return

        select_validado = (
            "TRY_CAST(validado AS BOOLEAN)"
            if "validado" in columns
            else "false"
        )
        select_status = (
            "CAST(status_validacao AS VARCHAR)"
            if "status_validacao" in columns
            else "CAST(status AS VARCHAR)"
            if "status" in columns
            else "'pendente'"
        )
        select_motivo = (
            "CAST(motivo_status AS VARCHAR)"
            if "motivo_status" in columns
            else "CAST(justificativa AS VARCHAR)"
            if "justificativa" in columns
            else "CAST(NULL AS VARCHAR)"
        )
        select_usuario = (
            "CAST(usuario AS VARCHAR)" if "usuario" in columns else "CAST(NULL AS VARCHAR)"
        )
        if "data_hora" in columns:
            select_data = "TRY_CAST(data_hora AS TIMESTAMP)"
        elif "data_hora_alteracao" in columns:
            select_data = "TRY_CAST(data_hora_alteracao AS TIMESTAMP)"
        elif "criado_em" in columns:
            select_data = "TRY_CAST(criado_em AS TIMESTAMP)"
        else:
            select_data = "CAST(NULL AS TIMESTAMP)"

        connection.execute(
            f"""
            CREATE TEMP TABLE gov AS
            SELECT
                CAST(chave_registro AS VARCHAR) AS chave_registro,
                {select_validado} AS validado,
                COALESCE({select_status}, 'pendente') AS status_validacao,
                {select_motivo} AS motivo_status,
                {select_usuario} AS usuario_validacao,
                {select_data} AS data_hora_validacao
            FROM log_raw
            WHERE chave_registro IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY CAST(chave_registro AS VARCHAR)
                ORDER BY {select_data} DESC NULLS LAST
            ) = 1
            """
        )

        connection.execute(
            """
            COPY (
                SELECT
                    src.*,
                    COALESCE(gov.validado, false) AS validado,
                    COALESCE(gov.status_validacao, 'pendente') AS status_validacao,
                    gov.motivo_status,
                    gov.usuario_validacao,
                    gov.data_hora_validacao
                FROM read_parquet(?) AS src
                LEFT JOIN gov
                  ON gov.chave_registro = CONCAT_WS(
                      '|',
                      CAST(src.NUM_INTRP_UCI AS VARCHAR),
                      CAST(src.NUM_POSTO_UCI AS VARCHAR),
                      CAST(src.NUM_UC_UCI AS VARCHAR)
                  )
            )
            TO ?
            (FORMAT PARQUET, COMPRESSION ZSTD)
            """,
            [str(source_path), str(output_path)],
        )

    def _count_governance_rows(self, connection: duckdb.DuckDBPyConnection) -> int:
        try:
            return connection.execute("SELECT COUNT(*) FROM gov").fetchone()[0]
        except Exception:
            return 0

    def _refresh_aliases(self, source_path: Path, output_path: Path) -> None:
        try:
            if source_path == APURACAO_ATUAL_PATH:
                if APURACAO_CORRIGIDO_ATUAL_PATH.exists():
                    APURACAO_CORRIGIDO_ATUAL_PATH.unlink()
                if output_path != APURACAO_CORRIGIDO_ATUAL_PATH:
                    copyfile(output_path, APURACAO_CORRIGIDO_ATUAL_PATH)
                return

            if output_path == OMS_UNION_CORRIGIDO_LEGACY_PARQUET_PATH:
                return
            if OMS_UNION_CORRIGIDO_LEGACY_PARQUET_PATH.exists():
                OMS_UNION_CORRIGIDO_LEGACY_PARQUET_PATH.unlink()
            copyfile(output_path, OMS_UNION_CORRIGIDO_LEGACY_PARQUET_PATH)
        except Exception:
            pass


OmsCorrigidoService = OmsCorrecoesService
OmsCorrectionService = OmsCorrecoesService
