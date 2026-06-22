from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
from fastapi import APIRouter, HTTPException, Query


router = APIRouter(prefix="/apuracao/filas", tags=["apuracao-filas"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PENDENCIAS_ATUAL = PROJECT_ROOT / "data" / "mart" / "apuracao" / "pendencias_APURACAO_ATUAL.parquet"


def _ensure_file() -> Path:
    if not PENDENCIAS_ATUAL.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Pendências materializadas não encontradas. "
                "Execute `python -m backend.scripts.validar_retomada_iqs --anomes 202605 "
                "--materializar-pendencias`."
            ),
        )
    return PENDENCIAS_ATUAL


def _rows_to_dicts(columns: list[str], rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [dict(zip(columns, row, strict=False)) for row in rows]


@router.get("/resumo")
def resumo_filas() -> dict[str, Any]:
    parquet_path = _ensure_file()

    with duckdb.connect(database=":memory:") as connection:
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
            """
            SELECT
                COALESCE(status_registro, 'pendente') AS status,
                COUNT(*) AS total
            FROM read_parquet(?)
            GROUP BY COALESCE(status_registro, 'pendente')
            ORDER BY total DESC
            """,
            [str(parquet_path)],
        ).fetchall()
        por_status = _rows_to_dicts(["status", "total"], por_status_rows)

    return {
        "arquivo": str(parquet_path),
        "status": "processado",
        "total_pendencias": total,
        "por_regra": por_regra,
        "por_status": por_status,
    }


@router.get("/{regra}")
def consultar_fila(
    regra: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    parquet_path = _ensure_file()

    with duckdb.connect(database=":memory:") as connection:
        total = connection.execute(
            """
            SELECT COUNT(*)
            FROM read_parquet(?)
            WHERE regra = ?
            """,
            [str(parquet_path), regra],
        ).fetchone()[0]

        result = connection.execute(
            """
            SELECT *
            FROM read_parquet(?)
            WHERE regra = ?
            ORDER BY prioridade DESC, chave_registro
            LIMIT ? OFFSET ?
            """,
            [str(parquet_path), regra, limit, offset],
        )
        columns = [column[0] for column in result.description]
        rows = result.fetchall()

    return {
        "arquivo": str(parquet_path),
        "regra": regra,
        "limit": limit,
        "offset": offset,
        "total": total,
        "registros": _rows_to_dicts(columns, rows),
    }

