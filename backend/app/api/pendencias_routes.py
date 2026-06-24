from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.app.services.pendencias_apuracao_service import PendenciasApuracaoService


router = APIRouter(prefix="/apuracao/pendencias", tags=["apuracao-pendencias"])


@router.get("/resumo")
def resumo_pendencias() -> dict[str, Any]:
    return PendenciasApuracaoService().resumo()


@router.get("")
def listar_pendencias(
    regra: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return PendenciasApuracaoService().listar(regra=regra, limit=limit, offset=offset)


@router.post("/materializar/{anomes}")
def materializar_pendencias(anomes: str) -> dict[str, Any]:
    try:
        result = PendenciasApuracaoService().materializar(anomes)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao materializar pendências: {type(exc).__name__}: {exc}",
        ) from exc

    return {
        "anomes": result.anomes,
        "origem": str(result.origem),
        "parquet": str(result.parquet),
        "parquet_atual": str(result.parquet_atual),
        "total_pendencias": result.total_pendencias,
        "horario_negativo": result.horario_negativo,
        "sobreposicao_interrupcao": result.sobreposicao_interrupcao,
        "sobreposicao_uc": result.sobreposicao_uc,
        "sem_causa_componente": result.sem_causa_componente,
    }
