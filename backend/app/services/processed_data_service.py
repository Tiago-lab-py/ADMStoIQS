from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

try:
    from backend.app.core.contracts import EXPORTS_DIR, MART_DIR, PROCESSED_DIR
except Exception:
    ROOT_DIR = Path(__file__).resolve().parents[3]
    PROCESSED_DIR = ROOT_DIR / "data" / "processed"
    MART_DIR = ROOT_DIR / "data" / "mart"
    EXPORTS_DIR = ROOT_DIR / "data" / "exports"

try:
    from backend.app.schemas.export_layout import CSV_EXPORT_COLUMNS
except Exception:
    CSV_EXPORT_COLUMNS = []


UNION_ANOMES = "UNION"
OMS_UNION_PARQUET = MART_DIR / "agrupamento_oms_UNION.parquet"
APURACAO_DIR = MART_DIR / "apuracao"
APURACAO_ATUAL = APURACAO_DIR / "agrupamento_oms_APURACAO_ATUAL.parquet"


def _rows_to_dicts(columns: list[str], rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [dict(zip(columns, row)) for row in rows]


def _parquet_path(anomes: str | None = None) -> Path:
    if not anomes or anomes.upper() == UNION_ANOMES:
        if APURACAO_ATUAL.exists():
            return APURACAO_ATUAL
        if OMS_UNION_PARQUET.exists():
            return OMS_UNION_PARQUET
        raise FileNotFoundError(
            f"Mart UNION não encontrado: {OMS_UNION_PARQUET}. "
            "Execute a etapa `Atualizar OMS UNION` ou rode "
            "`python -m backend.scripts.gerar_oms_union`."
        )

    apuracao = APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}.parquet"
    if apuracao.exists():
        return apuracao

    processed = PROCESSED_DIR / f"agrupamento_oms_{anomes}.parquet"
    if processed.exists():
        return processed

    raise FileNotFoundError(f"Parquet não encontrado para {anomes}.")


def _timestamp_expr(column: str) -> str:
    return f"""
        COALESCE(
            TRY_CAST({column} AS TIMESTAMP),
            TRY_STRPTIME(CAST({column} AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
            TRY_STRPTIME(CAST({column} AS VARCHAR), '%d/%m/%Y %H:%M:%S')
        )
    """


def _num_seq_expr() -> str:
    return """
        COALESCE(
            NULLIF(TRIM(CAST(NUM_SEQ_INTRP AS VARCHAR)), ''),
            NULLIF(TRIM(CAST(PID_INTRP_CONJTO_PIN AS VARCHAR)), ''),
            NULLIF(TRIM(CAST(NUM_INTRP_UCI AS VARCHAR)), '')
        )
    """


class ProcessedDataService:
    def list_competencias(self) -> dict[str, list[dict[str, Any]]]:
        competencias: list[dict[str, Any]] = []

        for path in sorted(PROCESSED_DIR.glob("agrupamento_oms_*.parquet")):
            anomes = path.stem.replace("agrupamento_oms_", "")
            competencias.append(
                {
                    "anomes": anomes,
                    "arquivo": path.name,
                    "caminho": str(path),
                    "tamanho_bytes": path.stat().st_size,
                    "modificado_em": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    "fonte": "processed",
                }
            )

        for path in sorted(APURACAO_DIR.glob("agrupamento_oms_APURACAO_*.parquet")):
            if path.name.endswith("_ATUAL.parquet"):
                continue
            anomes = path.stem.replace("agrupamento_oms_APURACAO_", "")
            competencias.append(
                {
                    "anomes": anomes,
                    "arquivo": path.name,
                    "caminho": str(path),
                    "tamanho_bytes": path.stat().st_size,
                    "modificado_em": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    "fonte": "apuracao",
                }
            )

        if OMS_UNION_PARQUET.exists():
            competencias.append(
                {
                    "anomes": UNION_ANOMES,
                    "arquivo": OMS_UNION_PARQUET.name,
                    "caminho": str(OMS_UNION_PARQUET),
                    "tamanho_bytes": OMS_UNION_PARQUET.stat().st_size,
                    "modificado_em": datetime.fromtimestamp(OMS_UNION_PARQUET.stat().st_mtime).isoformat(),
                    "fonte": "mart",
                }
            )

        if APURACAO_ATUAL.exists():
            competencias.append(
                {
                    "anomes": "APURACAO_ATUAL",
                    "arquivo": APURACAO_ATUAL.name,
                    "caminho": str(APURACAO_ATUAL),
                    "tamanho_bytes": APURACAO_ATUAL.stat().st_size,
                    "modificado_em": datetime.fromtimestamp(APURACAO_ATUAL.stat().st_mtime).isoformat(),
                    "fonte": "apuracao",
                }
            )

        return {"competencias": competencias}

    listar_competencias = list_competencias
    list_available_competencias = list_competencias

    def get_data(
        self,
        anomes: str | None = None,
        *,
        limit: int = 100,
        offset: int = 0,
        regional_origem: str | None = None,
    ) -> dict[str, Any]:
        path = _parquet_path(anomes)
        where = []
        params: list[Any] = [str(path)]
        if regional_origem:
            where.append("REGIONAL_ORIGEM = ?")
            params.append(regional_origem)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        query = f"""
            SELECT *
            FROM read_parquet(?)
            {where_sql}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        with duckdb.connect(database=":memory:") as connection:
            result = connection.execute(query, params)
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        return {
            "anomes": anomes or "APURACAO_ATUAL",
            "limit": limit,
            "offset": offset,
            "total_retornado": len(rows),
            "registros": _rows_to_dicts(columns, rows),
        }

    def get_mart_data(self, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        try:
            return self.get_data(UNION_ANOMES, limit=limit, offset=offset)
        except FileNotFoundError as error:
            return {
                "anomes": UNION_ANOMES,
                "limit": limit,
                "offset": offset,
                "total_retornado": 0,
                "registros": [],
                "status": "pendente",
                "mensagem": str(error),
            }

    def get_sample(self, anomes: str | None = None, *, limit: int = 100) -> dict[str, Any]:
        return self.get_data(anomes or UNION_ANOMES, limit=limit, offset=0)

    def get_mart_sample(self, *, limit: int = 100) -> dict[str, Any]:
        return self.get_sample(UNION_ANOMES, limit=limit)

    gerar_amostra = get_sample
    gerar_mart_amostra = get_mart_sample

    def get_mart_resumo(self) -> dict[str, Any]:
        try:
            from backend.app.services.apuracao_resumo_service import ApuracaoResumoService

            ApuracaoResumoService().materializar()
            resumo = ApuracaoResumoService().ler_atual()
            if resumo:
                return resumo
        except Exception:
            pass

        try:
            path = _parquet_path(UNION_ANOMES)
        except FileNotFoundError as error:
            return {
                "status": "pendente",
                "mensagem": str(error),
                "total_registros": 0,
                "pendencias_totais": 0,
                "pendentes": 0,
                "horario_negativo": 0,
                "sobreposicao_interrupcao": 0,
                "sobreposicoes": 0,
                "rejeitados": 0,
                "rejeitados_por_atividade": {},
            }
        with duckdb.connect(database=":memory:") as connection:
            total = connection.execute("SELECT count(*) FROM read_parquet(?)", [str(path)]).fetchone()[0]
            horario = self._count_horario_negativo(connection, path)
            sobreposicao = self._count_sobreposicao_interrupcao(connection, path)
            rejeitados = self._count_status(connection, path, "rejeitado")

        return {
            "total_registros": total,
            "pendencias_totais": max(total - rejeitados, 0),
            "pendentes": max(total - rejeitados, 0),
            "horario_negativo": horario,
            "sobreposicao_interrupcao": sobreposicao,
            "sobreposicoes": sobreposicao,
            "rejeitados": rejeitados,
            "rejeitados_por_atividade": {},
        }

    def get_treatment_data(
        self,
        tratamento: str,
        *,
        limit: int = 100,
        offset: int = 0,
        duracao_min: int | None = None,
        duracao_max: int | None = None,
    ) -> dict[str, Any]:
        if tratamento == "horario-negativo":
            return self.get_horario_negativo(
                limit=limit,
                offset=offset,
                duracao_min=duracao_min,
                duracao_max=duracao_max,
            )
        if tratamento == "sobreposicao-interrupcao":
            return self.get_sobreposicao_interrupcao(limit=limit, offset=offset)
        if tratamento == "sem-causa-componente":
            return self.get_sem_causa_componente(limit=limit, offset=offset)
        if tratamento == "sobreposicao-uc":
            return self.get_sobreposicao_uc(limit=limit, offset=offset)
        return self.get_data(UNION_ANOMES, limit=limit, offset=offset)

    def get_horario_negativo(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        duracao_min: int | None = None,
        duracao_max: int | None = None,
    ) -> dict[str, Any]:
        path = _parquet_path(UNION_ANOMES)
        inicio = _timestamp_expr("DATA_HORA_INIC_INTRP")
        fim = _timestamp_expr("DATA_HORA_FIM_INTRP")
        num_seq = _num_seq_expr()

        filtros = ["__duracao_minutos < 0"]
        params: list[Any] = [str(path)]
        if duracao_min is not None:
            filtros.append("__duracao_minutos >= ?")
            params.append(duracao_min)
        if duracao_max is not None:
            filtros.append("__duracao_minutos <= ?")
            params.append(duracao_max)

        where_sql = " AND ".join(filtros)
        query = f"""
            WITH base AS (
                SELECT
                    *,
                    {inicio} AS __inicio_ts,
                    {fim} AS __fim_ts,
                    {num_seq} AS __num_seq,
                    date_diff('minute', {inicio}, {fim}) AS __duracao_minutos
                FROM read_parquet(?)
            ),
            negativos AS (
                SELECT *
                FROM base
                WHERE __inicio_ts IS NOT NULL
                  AND __fim_ts IS NOT NULL
                  AND {where_sql}
                  AND __num_seq IS NOT NULL
            ),
            unicos AS (
                SELECT
                    __num_seq,
                    min(__inicio_ts) AS __inicio_ts,
                    min(__fim_ts) AS __fim_ts,
                    min(__duracao_minutos) AS duracao_minutos,
                    max(REGIONAL_ORIGEM) AS REGIONAL_ORIGEM,
                    max(ANOMES_PROCESSAMENTO) AS ANOMES_PROCESSAMENTO,
                    max(NUM_OPER_CHV_INTRP) AS NUM_OPER_CHV_INTRP,
                    max(NUM_OCORRENCIA_ADMS) AS NUM_OCORRENCIA_ADMS,
                    count(*) AS qtd_ucs_afetadas
                FROM negativos
                GROUP BY __num_seq
            )
            SELECT
                __num_seq AS NUM_SEQ_INTRP,
                NUM_OPER_CHV_INTRP,
                NUM_OCORRENCIA_ADMS,
                strftime(__inicio_ts, '%d/%m/%Y %H:%M:%S') AS DATA_HORA_INIC_INTRP,
                strftime(__fim_ts, '%d/%m/%Y %H:%M:%S') AS DATA_HORA_FIM_INTRP,
                duracao_minutos,
                qtd_ucs_afetadas,
                REGIONAL_ORIGEM,
                ANOMES_PROCESSAMENTO,
                'DATA_HORA_FIM_INTRP' AS CAMPO_SUGERIDO,
                CASE
                    WHEN duracao_minutos >= -180
                    THEN strftime(__inicio_ts + INTERVAL 3 HOUR, '%d/%m/%Y %H:%M:%S')
                    ELSE NULL
                END AS VALOR_SUGERIDO,
                CASE
                    WHEN duracao_minutos >= -180
                    THEN 'Sugerir ajuste de fuso: fim = início + 3 horas.'
                    ELSE 'Revisão manual: diferença negativa maior que 3 horas.'
                END AS SUGESTAO
            FROM unicos
            ORDER BY duracao_minutos ASC, NUM_SEQ_INTRP
            LIMIT ? OFFSET ?
        """
        data_params = [*params, limit, offset]

        count_query = f"""
            WITH base AS (
                SELECT
                    {inicio} AS __inicio_ts,
                    {fim} AS __fim_ts,
                    {num_seq} AS __num_seq,
                    date_diff('minute', {inicio}, {fim}) AS __duracao_minutos
                FROM read_parquet(?)
            )
            SELECT count(DISTINCT __num_seq)
            FROM base
            WHERE __inicio_ts IS NOT NULL
              AND __fim_ts IS NOT NULL
              AND {where_sql}
              AND __num_seq IS NOT NULL
        """

        with duckdb.connect(database=":memory:") as connection:
            result = connection.execute(query, data_params)
            columns = [column[0] for column in result.description]
            rows = result.fetchall()
            total = connection.execute(count_query, params).fetchone()[0]

        return {
            "tratamento": "horario-negativo",
            "limit": limit,
            "offset": offset,
            "total_retornado": len(rows),
            "total": total,
            "num_seq_intrp_distintas": total,
            "registros": _rows_to_dicts(columns, rows),
        }

    def get_sobreposicao_interrupcao(self, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        path = _parquet_path(UNION_ANOMES)
        inicio = _timestamp_expr("DATA_HORA_INIC_INTRP")
        fim = _timestamp_expr("DATA_HORA_FIM_INTRP")
        num_seq = _num_seq_expr()

        query = f"""
            WITH base AS (
                SELECT
                    *,
                    {inicio} AS __inicio_ts,
                    {fim} AS __fim_ts,
                    {num_seq} AS __num_seq
                FROM read_parquet(?)
                WHERE NULLIF(TRIM(CAST(NUM_OPER_CHV_INTRP AS VARCHAR)), '') IS NOT NULL
            ),
            interrupcoes AS (
                SELECT
                    NUM_OPER_CHV_INTRP,
                    __num_seq,
                    min(__inicio_ts) AS inicio_intrp,
                    max(__fim_ts) AS fim_intrp,
                    min(TRY_CAST(NUM_SEQ_INTRP AS BIGINT)) AS ordem_seq,
                    count(*) AS qtd_ucs_afetadas
                FROM base
                WHERE __inicio_ts IS NOT NULL
                  AND __fim_ts IS NOT NULL
                  AND __num_seq IS NOT NULL
                GROUP BY NUM_OPER_CHV_INTRP, __num_seq
            ),
            pares AS (
                SELECT
                    a.NUM_OPER_CHV_INTRP,
                    a.__num_seq AS NUM_SEQ_INTRP,
                    b.__num_seq AS NUM_SEQ_INTRP_SOBREPOSTA,
                    a.inicio_intrp,
                    a.fim_intrp,
                    b.inicio_intrp AS inicio_sobreposta,
                    b.fim_intrp AS fim_sobreposta,
                    a.qtd_ucs_afetadas,
                    CASE
                        WHEN COALESCE(a.ordem_seq, 9223372036854775807) <= COALESCE(b.ordem_seq, 9223372036854775807)
                        THEN 'manter'
                        ELSE 'sugerir_rejeitar'
                    END AS ACAO_SUGERIDA
                FROM interrupcoes a
                JOIN interrupcoes b
                  ON a.NUM_OPER_CHV_INTRP = b.NUM_OPER_CHV_INTRP
                 AND a.__num_seq <> b.__num_seq
                 AND a.inicio_intrp < b.fim_intrp
                 AND b.inicio_intrp < a.fim_intrp
            )
            SELECT DISTINCT
                NUM_OPER_CHV_INTRP,
                NUM_SEQ_INTRP,
                NUM_SEQ_INTRP_SOBREPOSTA,
                strftime(inicio_intrp, '%d/%m/%Y %H:%M:%S') AS DATA_HORA_INIC_INTRP,
                strftime(fim_intrp, '%d/%m/%Y %H:%M:%S') AS DATA_HORA_FIM_INTRP,
                strftime(inicio_sobreposta, '%d/%m/%Y %H:%M:%S') AS DATA_HORA_INIC_SOBREPOSTA,
                strftime(fim_sobreposta, '%d/%m/%Y %H:%M:%S') AS DATA_HORA_FIM_SOBREPOSTA,
                qtd_ucs_afetadas,
                ACAO_SUGERIDA,
                CASE WHEN ACAO_SUGERIDA = 'sugerir_rejeitar' THEN '91' ELSE NULL END AS NUM_MOTIVO_TRAT_DIF_UCI_SUGERIDO,
                'Sobreposição temporal no mesmo NUM_OPER_CHV_INTRP. Manter menor NUM_SEQ_INTRP.' AS SUGESTAO
            FROM pares
            WHERE ACAO_SUGERIDA = 'sugerir_rejeitar'
            ORDER BY NUM_OPER_CHV_INTRP, NUM_SEQ_INTRP
            LIMIT ? OFFSET ?
        """

        with duckdb.connect(database=":memory:") as connection:
            result = connection.execute(query, [str(path), limit, offset])
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        return {
            "tratamento": "sobreposicao-interrupcao",
            "limit": limit,
            "offset": offset,
            "total_retornado": len(rows),
            "registros": _rows_to_dicts(columns, rows),
        }

    def get_sobreposicao_uc(self, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return {"tratamento": "sobreposicao-uc", "limit": limit, "offset": offset, "total_retornado": 0, "registros": []}

    def get_sem_causa_componente(self, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        path = _parquet_path(UNION_ANOMES)
        query = """
            SELECT *
            FROM read_parquet(?)
            WHERE NULLIF(TRIM(CAST(COD_CAUSA_INTRP AS VARCHAR)), '') IS NULL
               OR NULLIF(TRIM(CAST(COD_COMP_INTRP AS VARCHAR)), '') IS NULL
            LIMIT ? OFFSET ?
        """
        with duckdb.connect(database=":memory:") as connection:
            result = connection.execute(query, [str(path), limit, offset])
            columns = [column[0] for column in result.description]
            rows = result.fetchall()
        return {
            "tratamento": "sem-causa-componente",
            "limit": limit,
            "offset": offset,
            "total_retornado": len(rows),
            "registros": _rows_to_dicts(columns, rows),
        }

    tratamento_horario_negativo = get_horario_negativo
    tratamento_sobreposicao_interrupcao = get_sobreposicao_interrupcao
    tratamento_sobreposicao_uc = get_sobreposicao_uc
    tratamento_sem_causa_componente = get_sem_causa_componente

    def export_csv(
        self,
        anomes: str | None = None,
        *,
        regional_origem: str | None = None,
        usuario: str | None = None,
        justificativa: str | None = None,
        todas_regionais: bool = False,
    ) -> dict[str, Any]:
        path = _parquet_path(anomes)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        regional_label = "TODAS" if todas_regionais or not regional_origem else regional_origem
        output = EXPORTS_DIR / f"agrupamento_oms_{regional_label}_{anomes or 'APURACAO'}_{timestamp}.csv"

        columns = CSV_EXPORT_COLUMNS or ["*"]
        select_sql = "*" if columns == ["*"] else ", ".join(f'"{column}"' for column in columns)
        where = ""
        params: list[Any] = [str(path)]
        if regional_origem and not todas_regionais:
            where = "WHERE REGIONAL_ORIGEM = ?"
            params.append(regional_origem)

        query = f"SELECT {select_sql} FROM read_parquet(?) {where}"
        with duckdb.connect(database=":memory:") as connection:
            result = connection.execute(query, params)
            result_columns = [column[0] for column in result.description]
            rows = result.fetchall()

        with output.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file, delimiter="|")
            writer.writerow(result_columns)
            writer.writerows(rows)

        return {
            "anomes": anomes or "APURACAO_ATUAL",
            "regional_origem": regional_label,
            "arquivo": output.name,
            "caminho": str(output),
            "tamanho_bytes": output.stat().st_size,
            "total_linhas": len(rows),
            "colunas": len(result_columns),
        }

    exportar_csv = export_csv

    def export_csv_regionais(self, anomes: str | None = None, **kwargs: Any) -> dict[str, Any]:
        regionais = ["CSL", "LES", "NRO", "NRT", "OES"]
        arquivos = [
            self.export_csv(anomes, regional_origem=regional, **kwargs)
            for regional in regionais
        ]
        return {"anomes": anomes or "APURACAO_ATUAL", "arquivos": arquivos}

    exportar_csv_regionais = export_csv_regionais
    export_all_regionals = export_csv_regionais
    exportar_todas_regionais = export_csv_regionais

    def _count_horario_negativo(self, connection: duckdb.DuckDBPyConnection, path: Path) -> int:
        inicio = _timestamp_expr("DATA_HORA_INIC_INTRP")
        fim = _timestamp_expr("DATA_HORA_FIM_INTRP")
        num_seq = _num_seq_expr()
        query = f"""
            WITH base AS (
                SELECT
                    {inicio} AS inicio,
                    {fim} AS fim,
                    {num_seq} AS num_seq
                FROM read_parquet(?)
            )
            SELECT count(DISTINCT num_seq)
            FROM base
            WHERE inicio IS NOT NULL
              AND fim IS NOT NULL
              AND fim < inicio
              AND num_seq IS NOT NULL
        """
        return int(connection.execute(query, [str(path)]).fetchone()[0] or 0)

    def _count_sobreposicao_interrupcao(self, connection: duckdb.DuckDBPyConnection, path: Path) -> int:
        inicio = _timestamp_expr("DATA_HORA_INIC_INTRP")
        fim = _timestamp_expr("DATA_HORA_FIM_INTRP")
        num_seq = _num_seq_expr()
        query = f"""
            WITH base AS (
                SELECT
                    NUM_OPER_CHV_INTRP,
                    {num_seq} AS num_seq,
                    {inicio} AS inicio,
                    {fim} AS fim
                FROM read_parquet(?)
                WHERE NULLIF(TRIM(CAST(NUM_OPER_CHV_INTRP AS VARCHAR)), '') IS NOT NULL
            ),
            intrp AS (
                SELECT NUM_OPER_CHV_INTRP, num_seq, min(inicio) AS inicio, max(fim) AS fim
                FROM base
                WHERE inicio IS NOT NULL AND fim IS NOT NULL AND num_seq IS NOT NULL
                GROUP BY NUM_OPER_CHV_INTRP, num_seq
            ),
            marcadas AS (
                SELECT DISTINCT a.num_seq
                FROM intrp a
                JOIN intrp b
                  ON a.NUM_OPER_CHV_INTRP = b.NUM_OPER_CHV_INTRP
                 AND a.num_seq <> b.num_seq
                 AND a.inicio < b.fim
                 AND b.inicio < a.fim
            )
            SELECT count(*) FROM marcadas
        """
        return int(connection.execute(query, [str(path)]).fetchone()[0] or 0)

    def _count_status(self, connection: duckdb.DuckDBPyConnection, path: Path, status: str) -> int:
        try:
            return int(
                connection.execute(
                    """
                    SELECT count(*)
                    FROM read_parquet(?)
                    WHERE lower(trim(CAST(status_validacao AS VARCHAR))) = lower(?)
                       OR lower(trim(CAST(STATUS_VALIDACAO AS VARCHAR))) = lower(?)
                    """,
                    [str(path), status, status],
                ).fetchone()[0]
                or 0
            )
        except Exception:
            return 0

    def copiar_apuracao_atual_para_nome_union_corrigido(self) -> Path:
        """Compatibilidade temporária para telas antigas que ainda procuram este nome."""
        origem = _parquet_path(UNION_ANOMES)
        destino = MART_DIR / "agrupamento_oms_UNION_corrigido.parquet"
        if origem.exists():
            shutil.copy2(origem, destino)
        return destino
