from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APURACAO_DIR = PROJECT_ROOT / "data" / "mart" / "apuracao"
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
EXPORTS_IQS_DIR = PROJECT_ROOT / "data" / "exports" / "iqs"

CSV_EXPORT_COLUMNS = [
    "PID_INTRP_CONJTO_PIN",
    "PID_POSTO_PIN",
    "INDIC_AREA_REDE_POSTO_PIN",
    "ALIM_INTRP_PIN",
    "ESTADO_INTRP",
    "ALIM_INTRP",
    "CAR_SE",
    "INDIC_INTRP_SE_ALIM",
    "NUM_OCORRENCIA_ADMS",
    "INDIC_INTRP_AT",
    "CONS_INTRP",
    "KVA_INTRP",
    "NUM_OPER_CHV_INTRP",
    "NUM_FUNCAO_ELET_HCAI",
    "DESC_INTRP",
    "VALID_POS_OPERACAO",
    "DATA_HORA_INIC_INTRP",
    "DATA_HORA_FIM_INTRP",
    "TIPO_EQP_INTRP",
    "COORD_X_INTRP",
    "COORD_Y_INTRP",
    "NUM_SEQ_INTRP",
    "COD_CAUSA_INTRP",
    "COD_COMP_INTRP",
    "COD_AREA_ELET_INTRP",
    "COD_GRUPO_COMP_INTRP",
    "COD_COND_CLIMA_INTRP",
    "COD_TIPO_INTRP",
    "INDIC_JUMP_INTRP",
    "NUM_PROTOC_JUSTIF_RESP_INTRP",
    "TIPO_PROTOC_JUSTIF_INTRP",
    "COD_CONJTO_ELET_ANEEL_INTRP",
    "INDIC_CALC_DMIC_INTRP",
    "INDIC_PONTO_CONEX_INTRP",
    "NUM_GEO_CHV_INTRP",
    "TIPO_REDE_CHV_INTRP",
    "TIPO_CHV_INTRP",
    "INDIC_PROPR_POSTO_INTRP",
    "TENSAO_OPER_ALIM_INTRP",
    "INDIC_DESLIG_ENT_SERV_INTRP",
    "INDIC_PROPR_CHVP_INTRP",
    "INDIC_CHVP_INIC_ALIM_INTRP",
    "PID",
    "PID_INTRP_UCI",
    "NUM_INTRP_UCI",
    "NUM_POSTO_UCI",
    "NUM_UC_UCI",
    "TIPO_SIT_UC_UCI",
    "DTHR_INICIO_INTRP_UC",
    "NUM_INTRP_INIC_MANOBRA_UCI",
    "NUM_MOTIVO_TRAT_DIF_UCI",
    "UC_ACESSANTE",
    "SIGLA_REGIONAL",
    "NUM_PROTOC_JUSTIF_RESP_UCI",
    "TIPO_PROTOC_JUSTIF_UCI",
    "PID_PIN",
    "INDIC_PROCES_IND_PIN",
    "INDIC_SIT_PROCES_INDIC_UCI",
]


def _sql_literal(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


@dataclass(frozen=True)
class TratamentoMassivoResult:
    anomes: str
    origem: Path
    sobreposicao: Path
    parquet: Path
    parquet_atual: Path
    log: Path
    total_original: int
    removido_horario_negativo: int
    removido_sem_causa_componente: int
    removido_sobreposicao_interrupcao: int
    total_final: int


@dataclass(frozen=True)
class ExportacaoIqsResult:
    anomes: str
    origem: Path
    arquivos: list[dict[str, object]]
    total_linhas: int
    total_arquivos: int


class TratamentoMassivoService:
    def __init__(
        self,
        apuracao_dir: Path = APURACAO_DIR,
        logs_dir: Path = LOGS_DIR,
        exports_dir: Path = EXPORTS_IQS_DIR,
    ) -> None:
        self.apuracao_dir = apuracao_dir
        self.logs_dir = logs_dir
        self.exports_dir = exports_dir

    def gerar_apuracao_tratada(self, anomes: str) -> TratamentoMassivoResult:
        origem = self.apuracao_dir / f"agrupamento_oms_APURACAO_{anomes}.parquet"
        sobreposicao = self.apuracao_dir / f"analise_sobreposicao_interrupcao_APURACAO_{anomes}.parquet"
        destino = self.apuracao_dir / f"agrupamento_oms_APURACAO_{anomes}_TRATADO.parquet"
        destino_atual = self.apuracao_dir / "agrupamento_oms_APURACAO_TRATADO_ATUAL.parquet"
        log_path = self.logs_dir / f"log_tratamento_massivo_{anomes}.parquet"
        temp_destino = destino.with_suffix(".tmp.parquet")
        temp_log = log_path.with_suffix(".tmp.parquet")

        if not origem.exists():
            raise FileNotFoundError(f"Apuração não encontrada: {origem}")
        if not sobreposicao.exists():
            raise FileNotFoundError(
                f"Análise de sobreposição não encontrada: {sobreposicao}. "
                f"Execute `python -m backend.scripts.materializar_sobreposicao_interrupcao --anomes {anomes}`."
            )

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.apuracao_dir.mkdir(parents=True, exist_ok=True)
        executado_em = datetime.now().isoformat(timespec="seconds")

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(
                """
                CREATE TEMP TABLE base AS
                SELECT
                    *,
                    COALESCE(
                        try_strptime(CAST(DATA_HORA_INIC_INTRP AS VARCHAR), '%d/%m/%Y %H:%M:%S'),
                        try_strptime(CAST(DATA_HORA_INIC_INTRP AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
                        try_cast(DATA_HORA_INIC_INTRP AS TIMESTAMP)
                    ) AS _inicio_ts,
                    COALESCE(
                        try_strptime(CAST(DATA_HORA_FIM_INTRP AS VARCHAR), '%d/%m/%Y %H:%M:%S'),
                        try_strptime(CAST(DATA_HORA_FIM_INTRP AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
                        try_cast(DATA_HORA_FIM_INTRP AS TIMESTAMP)
                    ) AS _fim_ts
                FROM read_parquet(?)
                """,
                [str(origem)],
            )
            connection.execute(
                """
                CREATE TEMP TABLE sobreposicao_excluir AS
                SELECT DISTINCT CAST(interrupcao AS VARCHAR) AS NUM_SEQ_INTRP
                FROM read_parquet(?)
                WHERE acao_sugerida = 'EXCLUIR'
                """,
                [str(sobreposicao)],
            )
            connection.execute(
                """
                CREATE TEMP TABLE flags AS
                SELECT
                    *,
                    _fim_ts < _inicio_ts AS flag_horario_negativo,
                    (
                        COD_CAUSA_INTRP IS NULL
                        OR TRIM(CAST(COD_CAUSA_INTRP AS VARCHAR)) = ''
                        OR COD_COMP_INTRP IS NULL
                        OR TRIM(CAST(COD_COMP_INTRP AS VARCHAR)) = ''
                    ) AS flag_sem_causa_componente,
                    CAST(NUM_SEQ_INTRP AS VARCHAR) IN (SELECT NUM_SEQ_INTRP FROM sobreposicao_excluir) AS flag_sobreposicao_interrupcao
                FROM base
                """
            )
            connection.execute(
                """
                CREATE TEMP TABLE tratado AS
                SELECT * EXCLUDE (
                    _inicio_ts,
                    _fim_ts,
                    flag_horario_negativo,
                    flag_sem_causa_componente,
                    flag_sobreposicao_interrupcao
                )
                FROM flags
                WHERE NOT flag_horario_negativo
                  AND NOT flag_sem_causa_componente
                  AND NOT flag_sobreposicao_interrupcao
                """
            )
            connection.execute(
                """
                CREATE TEMP TABLE log_tratamento AS
                SELECT
                    ? AS anomes,
                    ? AS executado_em,
                    CAST(NUM_SEQ_INTRP AS VARCHAR) AS NUM_SEQ_INTRP,
                    CAST(NUM_INTRP_UCI AS VARCHAR) AS NUM_INTRP_UCI,
                    CAST(NUM_POSTO_UCI AS VARCHAR) AS NUM_POSTO_UCI,
                    CAST(NUM_UC_UCI AS VARCHAR) AS NUM_UC_UCI,
                    CAST(REGIONAL_ORIGEM AS VARCHAR) AS REGIONAL_ORIGEM,
                    regra,
                    acao,
                    justificativa
                FROM (
                    SELECT
                        *,
                        'horario_negativo' AS regra,
                        'remover_csv_iqs' AS acao,
                        'DATA_HORA_FIM_INTRP menor que DATA_HORA_INIC_INTRP.' AS justificativa
                    FROM flags
                    WHERE flag_horario_negativo
                    UNION ALL
                    SELECT
                        *,
                        'sem_causa_componente' AS regra,
                        'remover_csv_iqs' AS acao,
                        'COD_CAUSA_INTRP ou COD_COMP_INTRP nulo/vazio.' AS justificativa
                    FROM flags
                    WHERE flag_sem_causa_componente
                    UNION ALL
                    SELECT
                        *,
                        'sobreposicao_interrupcao' AS regra,
                        'remover_csv_iqs' AS acao,
                        'NUM_SEQ_INTRP sugerida para exclusão por sobreposição de interrupção/equipamento.' AS justificativa
                    FROM flags
                    WHERE flag_sobreposicao_interrupcao
                )
                """,
                [anomes, executado_em],
            )

            total_original = connection.execute("SELECT COUNT(*) FROM flags").fetchone()[0]
            removido_horario_negativo = connection.execute(
                "SELECT COUNT(*) FROM flags WHERE flag_horario_negativo"
            ).fetchone()[0]
            removido_sem_causa_componente = connection.execute(
                "SELECT COUNT(*) FROM flags WHERE flag_sem_causa_componente"
            ).fetchone()[0]
            removido_sobreposicao_interrupcao = connection.execute(
                "SELECT COUNT(*) FROM flags WHERE flag_sobreposicao_interrupcao"
            ).fetchone()[0]
            total_final = connection.execute("SELECT COUNT(*) FROM tratado").fetchone()[0]

            connection.execute("COPY tratado TO ? (FORMAT PARQUET)", [str(temp_destino)])
            connection.execute("COPY log_tratamento TO ? (FORMAT PARQUET)", [str(temp_log)])

        temp_destino.replace(destino)
        temp_log.replace(log_path)
        shutil.copyfile(destino, destino_atual)

        return TratamentoMassivoResult(
            anomes=anomes,
            origem=origem,
            sobreposicao=sobreposicao,
            parquet=destino,
            parquet_atual=destino_atual,
            log=log_path,
            total_original=int(total_original or 0),
            removido_horario_negativo=int(removido_horario_negativo or 0),
            removido_sem_causa_componente=int(removido_sem_causa_componente or 0),
            removido_sobreposicao_interrupcao=int(removido_sobreposicao_interrupcao or 0),
            total_final=int(total_final or 0),
        )

    def exportar_csv_iqs(self, anomes: str) -> ExportacaoIqsResult:
        origem = self.apuracao_dir / f"agrupamento_oms_APURACAO_{anomes}_TRATADO.parquet"
        if not origem.exists():
            raise FileNotFoundError(
                f"Base tratada não encontrada: {origem}. "
                f"Execute `python -m backend.scripts.gerar_apuracao_tratada --anomes {anomes}`."
            )

        self.exports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        arquivos: list[dict[str, object]] = []

        with duckdb.connect(database=":memory:") as connection:
            colunas = [row[0] for row in connection.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)",
                [str(origem)],
            ).fetchall()]
            export_columns = [column for column in CSV_EXPORT_COLUMNS if column in colunas]
            missing_columns = [column for column in CSV_EXPORT_COLUMNS if column not in colunas]
            if missing_columns:
                raise ValueError(f"Colunas ausentes no parquet tratado: {', '.join(missing_columns)}")

            regionais = [
                row[0] or "SEM_REGIONAL"
                for row in connection.execute(
                    """
                    SELECT DISTINCT COALESCE(NULLIF(TRIM(CAST(REGIONAL_ORIGEM AS VARCHAR)), ''), 'SEM_REGIONAL') AS regional
                    FROM read_parquet(?)
                    ORDER BY regional
                    """,
                    [str(origem)],
                ).fetchall()
            ]

            for regional in regionais:
                safe_regional = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in regional)
                arquivo = self.exports_dir / f"agrupamento_oms_IQS_{safe_regional}_{anomes}_{timestamp}.csv"
                select_columns = ", ".join(f'"{column}"' for column in export_columns)
                origem_sql = _sql_literal(origem)
                regional_sql = _sql_literal(regional)
                arquivo_sql = _sql_literal(arquivo)
                connection.execute(
                    f"""
                    COPY (
                        SELECT {select_columns}
                        FROM read_parquet({origem_sql})
                        WHERE COALESCE(NULLIF(TRIM(CAST(REGIONAL_ORIGEM AS VARCHAR)), ''), 'SEM_REGIONAL') = {regional_sql}
                    )
                    TO {arquivo_sql}
                    (FORMAT CSV, HEADER, DELIMITER '|')
                    """
                )
                linhas = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM read_parquet(?)
                    WHERE COALESCE(NULLIF(TRIM(CAST(REGIONAL_ORIGEM AS VARCHAR)), ''), 'SEM_REGIONAL') = ?
                    """,
                    [str(origem), regional],
                ).fetchone()[0]
                arquivos.append(
                    {
                        "regional": regional,
                        "arquivo": arquivo.name,
                        "caminho": str(arquivo),
                        "linhas": int(linhas or 0),
                    }
                )

        return ExportacaoIqsResult(
            anomes=anomes,
            origem=origem,
            arquivos=arquivos,
            total_linhas=sum(int(item["linhas"]) for item in arquivos),
            total_arquivos=len(arquivos),
        )
