from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
from fastapi import APIRouter, HTTPException, Query


router = APIRouter(prefix="/apuracao/filas", tags=["apuracao-filas"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APURACAO_DIR = PROJECT_ROOT / "data" / "mart" / "apuracao"
PENDENCIAS_ATUAL = APURACAO_DIR / "pendencias_APURACAO_ATUAL.parquet"


def _ensure_file(anomes: str | None = None) -> Path:
    parquet_path = PENDENCIAS_ATUAL
    if anomes and anomes.upper() != "ATUAL":
        parquet_path = APURACAO_DIR / f"pendencias_APURACAO_{anomes}.parquet"

    if not parquet_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Pendências materializadas não encontradas. "
                f"Arquivo esperado: {parquet_path}. "
                "Execute `python -m backend.scripts.validar_retomada_iqs --anomes [AAAAMM] "
                "--materializar-pendencias`."
            ),
        )
    return parquet_path


def _rows_to_dicts(columns: list[str], rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [dict(zip(columns, row, strict=False)) for row in rows]


def _parquet_columns(connection: duckdb.DuckDBPyConnection, parquet_path: Path) -> list[str]:
    rows = connection.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(parquet_path)],
    ).fetchall()
    return [row[0] for row in rows]


def _first_existing(columns: list[str], candidates: list[str], default_sql: str) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return default_sql


@router.get("/resumo")
def resumo_filas(anomes: str | None = Query(default=None)) -> dict[str, Any]:
    parquet_path = _ensure_file(anomes)

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
        por_regra = _rows_to_dicts(["regra", "total", "registros_distintos"], por_regra_rows)

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
        por_status = _rows_to_dicts(["status", "total"], por_status_rows)

    return {
        "arquivo": str(parquet_path),
        "anomes": anomes or "ATUAL",
        "status": "processado",
        "total_pendencias": total,
        "por_regra": por_regra,
        "por_status": por_status,
    }


@router.get("/{regra}")
def consultar_fila(
    regra: str,
    anomes: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    parquet_path = _ensure_file(anomes)

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
