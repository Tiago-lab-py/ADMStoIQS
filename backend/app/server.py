from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI
from pathlib import Path
from typing import Any

import duckdb
from fastapi import HTTPException, Query, Request
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.iqs_routes import router as iqs_router
from backend.app.api.pendencias_routes import router as pendencias_router
from backend.app.api.routes import router as api_router
from backend.app.services.sobreposicao_interrupcao_service import SobreposicaoInterrupcaoService
from backend.app.services.tratamento_massivo_service import TratamentoMassivoService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APURACAO_DIR = PROJECT_ROOT / "data" / "mart" / "apuracao"
PENDENCIAS_ATUAL = APURACAO_DIR / "pendencias_APURACAO_ATUAL.parquet"
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
DECISOES_ATUAL = LOGS_DIR / "decisoes_pendencias_ATUAL.parquet"


class DecisaoGovernadaPayload(BaseModel):
    anomes: str = Field(default="202605", min_length=6, max_length=6)
    regra: str
    acao: str
    chaves_registro: list[str] = Field(default_factory=list)
    justificativa: str = Field(default="", max_length=2000)
    usuario: str = Field(default="admin", max_length=120)
    perfil: str = Field(default="admin", max_length=80)
    pc: str | None = Field(default=None, max_length=120)


def _ensure_pendencias_file(anomes: str | None = None) -> Path:
    parquet_path = PENDENCIAS_ATUAL
    if anomes and anomes.upper() != "ATUAL":
        parquet_path = APURACAO_DIR / f"pendencias_APURACAO_{anomes}.parquet"

    if not parquet_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Pendências materializadas não encontradas em {parquet_path}. "
                "Execute `python -m backend.scripts.validar_retomada_iqs --anomes [AAAAMM] "
                "--materializar-pendencias`."
            ),
        )
    return parquet_path


def _rows_to_dicts(columns: list[str], rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [dict(zip(columns, row, strict=False)) for row in rows]


def _decisoes_path(anomes: str) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"decisoes_pendencias_{anomes}.parquet"


def _parquet_columns(connection: duckdb.DuckDBPyConnection, parquet_path: Path) -> list[str]:
    result = connection.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(parquet_path)],
    ).fetchall()
    return [row[0] for row in result]


def _first_existing(columns: list[str], candidates: list[str], default_sql: str) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return default_sql


def create_app() -> FastAPI:
    app = FastAPI(
        title="ADMStoIQS API",
        version="0.4.0",
        description="API local para ingestão, apuração, IQS e governança dos dados OMS/ADMS.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root() -> dict[str, str]:
        return {"status": "ok", "app": "ADMStoIQS API"}

    @app.get("/apuracao/filas/resumo")
    def resumo_filas(anomes: str | None = Query(default=None)) -> dict[str, Any]:
        parquet_path = _ensure_pendencias_file(anomes)

        with duckdb.connect(database=":memory:") as connection:
            columns = _parquet_columns(connection, parquet_path)
            status_expression = _first_existing(
                columns,
                ["status_registro", "status_pendencia", "status"],
                "'pendente'",
            )
            total = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(parquet_path)],
            ).fetchone()[0]
            por_regra_rows = connection.execute(
                """
                SELECT
                    regra,
                    COUNT(*) AS total,
                    COUNT(DISTINCT chave_registro) AS registros_distintos
                FROM read_parquet(?)
                GROUP BY regra
                ORDER BY total DESC
                """,
                [str(parquet_path)],
            ).fetchall()
            por_status_rows = connection.execute(
                f"""
                SELECT
                    COALESCE({status_expression}, 'pendente') AS status,
                    COUNT(*) AS total
                FROM read_parquet(?)
                GROUP BY COALESCE({status_expression}, 'pendente')
                ORDER BY total DESC
                """,
                [str(parquet_path)],
            ).fetchall()

        return {
            "arquivo": str(parquet_path),
            "anomes": anomes or "ATUAL",
            "status": "processado",
            "total_pendencias": total,
            "por_regra": _rows_to_dicts(["regra", "total", "registros_distintos"], por_regra_rows),
            "por_status": _rows_to_dicts(["status", "total"], por_status_rows),
        }

    @app.get("/apuracao/filas/{regra}")
    def consultar_fila(
        regra: str,
        anomes: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        parquet_path = _ensure_pendencias_file(anomes)

        with duckdb.connect(database=":memory:") as connection:
            columns = _parquet_columns(connection, parquet_path)
            order_columns = []
            if "prioridade" in columns:
                order_columns.append("prioridade DESC")
            if "gravidade" in columns:
                order_columns.append("gravidade DESC")
            if "chave_registro" in columns:
                order_columns.append("chave_registro")
            order_sql = ", ".join(order_columns) if order_columns else "regra"
            total = connection.execute(
                """
                SELECT COUNT(*)
                FROM read_parquet(?)
                WHERE regra = ?
                """,
                [str(parquet_path), regra],
            ).fetchone()[0]
            result = connection.execute(
                f"""
                SELECT *
                FROM read_parquet(?)
                WHERE regra = ?
                ORDER BY {order_sql}
                LIMIT ? OFFSET ?
                """,
                [str(parquet_path), regra, limit, offset],
            )
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        return {
            "arquivo": str(parquet_path),
            "anomes": anomes or "ATUAL",
            "regra": regra,
            "limit": limit,
            "offset": offset,
            "total": total,
            "registros": _rows_to_dicts(columns, rows),
        }

    @app.post("/apuracao/analises/sobreposicao-interrupcao/materializar/{anomes}")
    def materializar_sobreposicao_interrupcao(anomes: str) -> dict[str, Any]:
        try:
            result = SobreposicaoInterrupcaoService().materializar(anomes)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        return {
            "anomes": result.anomes,
            "origem": str(result.origem),
            "parquet": str(result.parquet),
            "parquet_atual": str(result.parquet_atual),
            "total_interrupcoes": result.total_interrupcoes,
            "manter": result.manter,
            "excluir": result.excluir,
            "status": "processado",
        }

    @app.get("/apuracao/analises/sobreposicao-interrupcao")
    def consultar_sobreposicao_interrupcao(
        anomes: str = Query(default="202605"),
        situacao: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        parquet_path = APURACAO_DIR / f"analise_sobreposicao_interrupcao_APURACAO_{anomes}.parquet"
        if not parquet_path.exists():
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Análise não encontrada: {parquet_path}. "
                    f"Execute POST /apuracao/analises/sobreposicao-interrupcao/materializar/{anomes}."
                ),
            )

        filters = []
        params: list[Any] = [str(parquet_path)]
        if situacao:
            filters.append("acao_sugerida = ?")
            params.append(situacao.upper())
        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

        with duckdb.connect(database=":memory:") as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM read_parquet(?) {where_sql}",
                params,
            ).fetchone()[0]
            resumo_rows = connection.execute(
                """
                SELECT acao_sugerida, COUNT(*) AS total
                FROM read_parquet(?)
                GROUP BY acao_sugerida
                ORDER BY total DESC
                """,
                [str(parquet_path)],
            ).fetchall()
            result = connection.execute(
                f"""
                SELECT *
                FROM read_parquet(?)
                {where_sql}
                ORDER BY NUMERO_OPERACIONAL, DATA_INICIO, SITUACAO DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        return {
            "anomes": anomes,
            "arquivo": str(parquet_path),
            "situacao": situacao,
            "limit": limit,
            "offset": offset,
            "total": total,
            "resumo": _rows_to_dicts(["acao_sugerida", "total"], resumo_rows),
            "registros": _rows_to_dicts(columns, rows),
        }

    @app.get("/apuracao/decisoes/resumo")
    def resumo_decisoes(anomes: str = Query(default="202605")) -> dict[str, Any]:
        decisoes_path = _decisoes_path(anomes)
        if not decisoes_path.exists():
            return {
                "anomes": anomes,
                "arquivo": str(decisoes_path),
                "arquivo_atual": str(DECISOES_ATUAL),
                "total_decisoes": 0,
                "por_acao": [],
                "por_regra": [],
                "status": "sem_decisoes",
            }

        with duckdb.connect(database=":memory:") as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(decisoes_path)],
            ).fetchone()[0]
            por_acao_rows = connection.execute(
                """
                SELECT acao, COUNT(*) AS total
                FROM read_parquet(?)
                GROUP BY acao
                ORDER BY total DESC
                """,
                [str(decisoes_path)],
            ).fetchall()
            por_regra_rows = connection.execute(
                """
                SELECT regra, acao, COUNT(*) AS total
                FROM read_parquet(?)
                GROUP BY regra, acao
                ORDER BY regra, total DESC
                """,
                [str(decisoes_path)],
            ).fetchall()

        return {
            "anomes": anomes,
            "arquivo": str(decisoes_path),
            "arquivo_atual": str(DECISOES_ATUAL),
            "total_decisoes": total,
            "por_acao": _rows_to_dicts(["acao", "total"], por_acao_rows),
            "por_regra": _rows_to_dicts(["regra", "acao", "total"], por_regra_rows),
            "status": "processado",
        }

    @app.post("/tratamento-massivo/{anomes}/gerar")
    def gerar_tratamento_massivo(anomes: str) -> dict[str, Any]:
        try:
            result = TratamentoMassivoService().gerar_apuracao_tratada(anomes)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        return {
            "anomes": result.anomes,
            "origem": str(result.origem),
            "sobreposicao": str(result.sobreposicao),
            "parquet": str(result.parquet),
            "parquet_atual": str(result.parquet_atual),
            "log": str(result.log),
            "total_original": result.total_original,
            "removido_horario_negativo": result.removido_horario_negativo,
            "removido_sem_causa_componente": result.removido_sem_causa_componente,
            "removido_sobreposicao_interrupcao": result.removido_sobreposicao_interrupcao,
            "total_final": result.total_final,
            "status": "processado",
        }

    @app.get("/tratamento-massivo/{anomes}/resumo")
    def resumo_tratamento_massivo(anomes: str) -> dict[str, Any]:
        parquet = APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}_TRATADO.parquet"
        log_path = LOGS_DIR / f"log_tratamento_massivo_{anomes}.parquet"
        if not parquet.exists():
            return {
                "anomes": anomes,
                "parquet": str(parquet),
                "log": str(log_path),
                "status": "pendente",
                "total_final": 0,
                "remocoes": [],
            }

        with duckdb.connect(database=":memory:") as connection:
            total_final = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(parquet)],
            ).fetchone()[0]
            remocoes = []
            if log_path.exists():
                rows = connection.execute(
                    """
                    SELECT regra, COUNT(*) AS total
                    FROM read_parquet(?)
                    GROUP BY regra
                    ORDER BY total DESC
                    """,
                    [str(log_path)],
                ).fetchall()
                remocoes = _rows_to_dicts(["regra", "total"], rows)

        return {
            "anomes": anomes,
            "parquet": str(parquet),
            "log": str(log_path),
            "status": "processado",
            "total_final": total_final,
            "remocoes": remocoes,
        }

    @app.post("/tratamento-massivo/{anomes}/exportar-csv")
    def exportar_tratamento_massivo(anomes: str) -> dict[str, Any]:
        try:
            result = TratamentoMassivoService().exportar_csv_iqs(anomes)
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        return {
            "anomes": result.anomes,
            "origem": str(result.origem),
            "total_arquivos": result.total_arquivos,
            "total_linhas": result.total_linhas,
            "arquivos": result.arquivos,
            "status": "processado",
        }

    @app.get("/apuracao/decisoes/log")
    def consultar_decisoes_log(
        anomes: str = Query(default="202605"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        decisoes_path = _decisoes_path(anomes)
        if not decisoes_path.exists():
            return {
                "anomes": anomes,
                "arquivo": str(decisoes_path),
                "limit": limit,
                "offset": offset,
                "total": 0,
                "registros": [],
            }

        with duckdb.connect(database=":memory:") as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(decisoes_path)],
            ).fetchone()[0]
            result = connection.execute(
                """
                SELECT *
                FROM read_parquet(?)
                ORDER BY criado_em DESC, id_decisao DESC
                LIMIT ? OFFSET ?
                """,
                [str(decisoes_path), limit, offset],
            )
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        return {
            "anomes": anomes,
            "arquivo": str(decisoes_path),
            "limit": limit,
            "offset": offset,
            "total": total,
            "registros": _rows_to_dicts(columns, rows),
        }

    @app.post("/apuracao/decisoes")
    def registrar_decisao(payload: DecisaoGovernadaPayload, request: Request) -> dict[str, Any]:
        if payload.acao not in {"validar", "rejeitar", "ignorar_regra"}:
            raise HTTPException(
                status_code=422,
                detail="Ação inválida. Use validar, rejeitar ou ignorar_regra.",
            )
        if not payload.chaves_registro:
            raise HTTPException(status_code=422, detail="Informe ao menos uma chave_registro.")
        if not payload.justificativa.strip():
            raise HTTPException(status_code=422, detail="Justificativa é obrigatória.")

        decisoes_path = _decisoes_path(payload.anomes)
        temp_path = decisoes_path.with_suffix(".tmp.parquet")
        id_lote = str(uuid4())
        criado_em = datetime.now().isoformat(timespec="seconds")
        client_ip = request.client.host if request.client else ""
        pc = payload.pc or request.headers.get("x-pc-name") or ""

        rows = [
            {
                "id_decisao": str(uuid4()),
                "id_lote": id_lote,
                "anomes": payload.anomes,
                "regra": payload.regra,
                "acao": payload.acao,
                "chave_registro": chave,
                "justificativa": payload.justificativa.strip(),
                "usuario": payload.usuario,
                "perfil": payload.perfil,
                "pc": pc,
                "ip": client_ip,
                "origem": "portal_gestor",
                "status_decisao": "registrada",
                "criado_em": criado_em,
            }
            for chave in payload.chaves_registro
        ]

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(
                """
                CREATE TEMP TABLE novas_decisoes (
                    id_decisao VARCHAR,
                    id_lote VARCHAR,
                    anomes VARCHAR,
                    regra VARCHAR,
                    acao VARCHAR,
                    chave_registro VARCHAR,
                    justificativa VARCHAR,
                    usuario VARCHAR,
                    perfil VARCHAR,
                    pc VARCHAR,
                    ip VARCHAR,
                    origem VARCHAR,
                    status_decisao VARCHAR,
                    criado_em VARCHAR
                )
                """
            )
            connection.executemany(
                """
                INSERT INTO novas_decisoes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["id_decisao"],
                        row["id_lote"],
                        row["anomes"],
                        row["regra"],
                        row["acao"],
                        row["chave_registro"],
                        row["justificativa"],
                        row["usuario"],
                        row["perfil"],
                        row["pc"],
                        row["ip"],
                        row["origem"],
                        row["status_decisao"],
                        row["criado_em"],
                    )
                    for row in rows
                ],
            )
            if decisoes_path.exists():
                connection.execute(
                    """
                    CREATE TEMP TABLE decisoes AS
                    SELECT * FROM read_parquet(?)
                    UNION ALL
                    SELECT * FROM novas_decisoes
                    """,
                    [str(decisoes_path)],
                )
            else:
                connection.execute("CREATE TEMP TABLE decisoes AS SELECT * FROM novas_decisoes")

            total = connection.execute("SELECT COUNT(*) FROM decisoes").fetchone()[0]
            connection.execute(
                "COPY decisoes TO ? (FORMAT PARQUET)",
                [str(temp_path)],
            )

        temp_path.replace(decisoes_path)
        with duckdb.connect(database=":memory:") as connection:
            connection.execute(
                "COPY (SELECT * FROM read_parquet(?)) TO ? (FORMAT PARQUET)",
                [str(decisoes_path), str(DECISOES_ATUAL)],
            )

        return {
            "id_lote": id_lote,
            "anomes": payload.anomes,
            "regra": payload.regra,
            "acao": payload.acao,
            "decisoes_registradas": len(rows),
            "total_decisoes": total,
            "arquivo": str(decisoes_path),
            "arquivo_atual": str(DECISOES_ATUAL),
            "status": "registrado",
        }

    app.include_router(api_router)
    app.include_router(iqs_router)
    app.include_router(pendencias_router)

    return app


app = create_app()
