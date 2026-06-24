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

from backend.app.api.filas_routes import router as filas_router
from backend.app.api.iqs_routes import router as iqs_router
from backend.app.api.pendencias_routes import router as pendencias_router
from backend.app.api.routes import router as api_router
from backend.app.services.indicadores_continuidade_service import IndicadoresContinuidadeService
from backend.app.services.ressarcimento_service_v2 import RessarcimentoService
from backend.app.services.sobreposicao_interrupcao_service import SobreposicaoInterrupcaoService
from backend.app.services.sobreposicao_uc_service import SobreposicaoUcService
from backend.app.services.sobreposicao_uc_fase2_service import SobreposicaoUcFase2Service
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

    @app.post("/apuracao/analises/sobreposicao-uc/materializar/{anomes}")
    def materializar_sobreposicao_uc(anomes: str) -> dict[str, Any]:
        try:
            result = SobreposicaoUcService().materializar(anomes)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        return {
            "anomes": result.anomes,
            "origem": str(result.origem),
            "parquet": str(result.parquet),
            "parquet_atual": str(result.parquet_atual),
            "registros_classificar_91": result.registros_classificar_91,
            "ucs_afetadas": result.ucs_afetadas,
            "interrupcoes_afetadas": result.interrupcoes_afetadas,
            "horas_uc_reduzidas": result.horas_uc_reduzidas,
            "chi_reduzido_estimado": result.chi_reduzido_estimado,
            "status": "processado",
        }

    @app.get("/apuracao/analises/sobreposicao-uc")
    def consultar_sobreposicao_uc(
        anomes: str = Query(default="202605"),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        try:
            return SobreposicaoUcService().consultar(
                anomes=anomes,
                limit=limit,
                offset=offset,
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/apuracao/analises/sobreposicao-uc/implantar/{anomes}")
    def implantar_sobreposicao_uc(
        anomes: str,
        request: Request,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = payload or {}
        usuario = str(body.get("usuario") or body.get("user") or "sistema")
        perfil = str(body.get("perfil") or body.get("profile") or "gestor")
        justificativa = str(
            body.get("justificativa")
            or "Implantação governada de motivo 91 por sobreposição temporal de UC."
        )
        pc = str(body.get("pc") or body.get("host") or request.headers.get("x-workstation") or "")
        ip = request.client.host if request.client else ""
        recalcular = bool(body.get("recalcular", True))

        try:
            result = SobreposicaoUcService().implantar(
                anomes=anomes,
                usuario=usuario,
                perfil=perfil,
                justificativa=justificativa,
                ip=ip,
                pc=pc,
                recalcular=recalcular,
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        return {
            "anomes": result.anomes,
            "origem": str(result.origem),
            "backup": str(result.backup),
            "analise": str(result.analise),
            "log": str(result.log),
            "log_atual": str(result.log_atual),
            "registros_atualizados": result.registros_atualizados,
            "ucs_afetadas": result.ucs_afetadas,
            "interrupcoes_afetadas": result.interrupcoes_afetadas,
            "chi_reduzido_estimado": result.chi_reduzido_estimado,
            "recalculos": result.recalculos,
            "status": "implantado",
        }

    @app.post("/apuracao/analises/sobreposicao-uc-fase2/materializar/{anomes}")
    def materializar_sobreposicao_uc_fase2(anomes: str) -> dict[str, Any]:
        result = SobreposicaoUcFase2Service().materializar(anomes)
        return {
            "anomes": result.anomes,
            "origem": result.origem,
            "parquet": result.parquet,
            "parquet_atual": result.parquet_atual,
            "total_ajustes": result.total_ajustes,
            "ucs_afetadas": result.ucs_afetadas,
            "interrupcoes_ajustadas": result.interrupcoes_ajustadas,
            "minutos_interseccao": result.minutos_interseccao,
            "status": "processado",
        }

    @app.get("/apuracao/analises/sobreposicao-uc-fase2")
    def listar_sobreposicao_uc_fase2(
        anomes: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        return SobreposicaoUcFase2Service().listar(anomes=anomes, limit=limit, offset=offset)

    @app.post("/apuracao/analises/sobreposicao-uc-fase2/implantar/{anomes}")
    def implantar_sobreposicao_uc_fase2(
        anomes: str,
        request: Request,
        payload: dict[str, Any] | None = Body(default=None),
    ) -> dict[str, Any]:
        payload = payload or {}
        request_ip = request.client.host if request.client else ""
        result = SobreposicaoUcFase2Service().implantar(
            anomes=anomes,
            usuario=str(payload.get("usuario") or "api"),
            perfil=str(payload.get("perfil") or "admin"),
            ip=str(payload.get("ip") or request_ip),
            pc=str(payload.get("pc") or ""),
            justificativa=str(
                payload.get("justificativa")
                or "Implantação governada da Fase 2 de sobreposição UC."
            ),
            recalcular=bool(payload.get("recalcular", True)),
        )
        return {
            "anomes": result.anomes,
            "origem": result.origem,
            "backup": result.backup,
            "analise": result.analise,
            "log": result.log,
            "log_atual": result.log_atual,
            "registros_atualizados": result.registros_atualizados,
            "ucs_afetadas": result.ucs_afetadas,
            "interrupcoes_ajustadas": result.interrupcoes_ajustadas,
            "minutos_interseccao": result.minutos_interseccao,
            "recalculos": result.recalculos,
            "status": "processado",
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

    @app.post("/indicadores/continuidade/{anomes}/materializar")
    def materializar_indicadores_continuidade(anomes: str) -> dict[str, Any]:
        try:
            result = IndicadoresContinuidadeService().materializar(anomes)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        return {
            "anomes": result.anomes,
            "origem_antes": str(result.origem_antes),
            "origem_depois": str(result.origem_depois),
            "mart_uc": str(result.mart_uc),
            "mart_agregado": str(result.mart_agregado),
            "mart_comparativo": str(result.mart_comparativo),
            "total_uc": result.total_uc,
            "total_agregado": result.total_agregado,
            "total_comparativo": result.total_comparativo,
            "fonte_denominador": result.fonte_denominador,
            "filtro_faturamento": result.filtro_faturamento,
            "status": "processado",
        }

    @app.get("/indicadores/continuidade/{anomes}/resumo")
    def resumo_indicadores_continuidade(anomes: str) -> dict[str, Any]:
        comparativo_path = PROJECT_ROOT / "data" / "mart" / "indicadores" / f"indicadores_comparativo_{anomes}.parquet"
        if not comparativo_path.exists():
            return {
                "anomes": anomes,
                "arquivo": str(comparativo_path),
                "status": "pendente",
                "copel": None,
                "regionais": [],
            }

        with duckdb.connect(database=":memory:") as connection:
            copel_result = connection.execute(
                """
                SELECT *
                FROM read_parquet(?)
                WHERE nivel = 'COPEL'
                LIMIT 1
                """,
                [str(comparativo_path)],
            )
            copel_columns = [column[0] for column in copel_result.description]
            copel_rows = copel_result.fetchall()
            regionais_result = connection.execute(
                """
                SELECT *
                FROM read_parquet(?)
                WHERE nivel = 'REGIONAL'
                ORDER BY regional_origem
                """,
                [str(comparativo_path)],
            )
            regionais_columns = [column[0] for column in regionais_result.description]
            regionais_rows = regionais_result.fetchall()

        return {
            "anomes": anomes,
            "arquivo": str(comparativo_path),
            "status": "processado",
            "copel": _rows_to_dicts(copel_columns, copel_rows)[0] if copel_rows else None,
            "regionais": _rows_to_dicts(regionais_columns, regionais_rows),
        }

    @app.get("/indicadores/continuidade/{anomes}/comparativo")
    def consultar_indicadores_comparativo(
        anomes: str,
        nivel: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        comparativo_path = PROJECT_ROOT / "data" / "mart" / "indicadores" / f"indicadores_comparativo_{anomes}.parquet"
        if not comparativo_path.exists():
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Indicadores não encontrados: {comparativo_path}. "
                    f"Execute POST /indicadores/continuidade/{anomes}/materializar."
                ),
            )

        filters = []
        params: list[Any] = [str(comparativo_path)]
        if nivel:
            filters.append("nivel = ?")
            params.append(nivel.upper())
        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

        with duckdb.connect(database=":memory:") as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM read_parquet(?) {where_sql}",
                params,
            ).fetchone()[0]
            result = connection.execute(
                f"""
                SELECT *
                FROM read_parquet(?)
                {where_sql}
                ORDER BY nivel, regional_origem, cod_conjunto_aneel
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        return {
            "anomes": anomes,
            "arquivo": str(comparativo_path),
            "nivel": nivel,
            "limit": limit,
            "offset": offset,
            "total": total,
            "registros": _rows_to_dicts(columns, rows),
        }

    @app.post("/indicadores/ressarcimento/{anomes}/materializar")
    def materializar_ressarcimento(anomes: str) -> dict[str, Any]:
        try:
            result = RessarcimentoService().materializar(anomes)
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        return {
            "anomes": result.anomes,
            "origem_indicadores": str(result.origem_indicadores),
            "origem_metas": str(result.origem_metas),
            "origem_vrc": str(result.origem_vrc) if result.origem_vrc else None,
            "parquet": str(result.parquet),
            "parquet_atual": str(result.parquet_atual),
            "total_registros": result.total_registros,
            "total_ucs": result.total_ucs,
            "violacoes_antes": result.violacoes_antes,
            "violacoes_depois": result.violacoes_depois,
            "valor_estimado_antes": result.valor_estimado_antes,
            "valor_estimado_depois": result.valor_estimado_depois,
            "status_formula": result.status_formula,
            "status": "processado",
        }

    @app.get("/indicadores/ressarcimento/{anomes}/resumo")
    def resumo_ressarcimento(anomes: str) -> dict[str, Any]:
        return RessarcimentoService().resumo(anomes)

    @app.get("/indicadores/ressarcimento/{anomes}/dados")
    def consultar_ressarcimento(
        anomes: str,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        apenas_violacao: bool = Query(default=True),
    ) -> dict[str, Any]:
        try:
            return RessarcimentoService().dados(
                anomes=anomes,
                limit=limit,
                offset=offset,
                apenas_violacao=apenas_violacao,
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

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
    app.include_router(filas_router)

    return app


app = create_app()
