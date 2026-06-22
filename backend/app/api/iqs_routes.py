from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.iqs_settings import get_iqs_settings
from backend.app.services.iqs_mart_service import IQS_RAW_DIR, IqsMartService


router = APIRouter(prefix="/iqs", tags=["iqs"])


@router.get("/config")
def consultar_config_iqs() -> dict[str, Any]:
    """Retorna configuração IQS mascarada para diagnóstico operacional."""
    settings = get_iqs_settings()
    return settings.masked()


@router.get("/resumo")
def consultar_resumo_iqs(
    refresh: bool = Query(default=False),
    anomes: str = Query(default="202605"),
) -> dict[str, Any]:
    """Retorna o resumo atual dos marts IQS materializados."""
    if refresh:
        result = IqsMartService().materializar(anomes)
        return {
            "arquivos": [
                {
                    "anomes": result.anomes,
                    "fonte": arquivo.fonte,
                    "raw_path": str(arquivo.raw_path),
                    "mart_path": str(arquivo.mart_path),
                    "linhas_raw": arquivo.linhas_raw,
                    "linhas_mart": arquivo.linhas_mart,
                    "status": arquivo.status,
                    "erro": arquivo.erro,
                }
                for arquivo in result.arquivos
            ],
            "total_fontes": len(result.arquivos),
            "fontes_processadas": sum(1 for arquivo in result.arquivos if arquivo.status == "processado"),
            "status": "processado",
            "resumo": str(result.resumo_path),
            "resumo_atual": str(result.resumo_atual_path),
        }

    resumo = IqsMartService().ler_resumo_atual()
    if resumo is None:
        return {
            "arquivos": [],
            "total_fontes": 0,
            "fontes_processadas": 0,
            "status": "sem_resumo",
            "mensagem": "Resumo IQS ainda não materializado.",
        }

    resumo["status"] = "processado"
    return resumo


@router.get("/raw")
def listar_raw_iqs() -> dict[str, Any]:
    """Lista arquivos raw IQS disponíveis localmente."""
    arquivos = []
    if IQS_RAW_DIR.exists():
        for path in sorted(IQS_RAW_DIR.glob("*.parquet")):
            arquivos.append(
                {
                    "arquivo": path.name,
                    "caminho": str(path),
                    "tamanho_bytes": path.stat().st_size,
                }
            )

    return {
        "diretorio": str(IQS_RAW_DIR),
        "total": len(arquivos),
        "arquivos": arquivos,
    }


@router.post("/materializar/{anomes}")
def materializar_iqs(anomes: str) -> dict[str, Any]:
    """Materializa marts IQS a partir dos arquivos raw já extraídos."""
    try:
        result = IqsMartService().materializar(anomes)
    except Exception as exc:
        return {
            "anomes": anomes,
            "status": "erro",
            "erro": f"{type(exc).__name__}: {exc}",
            "arquivos": [],
        }

    return {
        "status": "processado",
        "anomes": result.anomes,
        "resumo": str(result.resumo_path),
        "resumo_atual": str(result.resumo_atual_path),
        "arquivos": [
            {
                "fonte": arquivo.fonte,
                "status": arquivo.status,
                "raw_path": str(arquivo.raw_path),
                "mart_path": str(arquivo.mart_path),
                "linhas_raw": arquivo.linhas_raw,
                "linhas_mart": arquivo.linhas_mart,
                "erro": arquivo.erro,
            }
            for arquivo in result.arquivos
        ],
    }


@router.post("/materializar-fonte/{fonte}/{anomes}")
def materializar_fonte_iqs(fonte: str, anomes: str) -> dict[str, Any]:
    """Materializa uma fonte IQS sob demanda, como metas_uc anual."""
    try:
        arquivo = IqsMartService().materializar_fonte_sob_demanda(fonte=fonte, anomes=anomes)
    except Exception as exc:
        return {
            "fonte": fonte,
            "anomes": anomes,
            "status": "erro",
            "erro": f"{type(exc).__name__}: {exc}",
        }

    return {
        "fonte": arquivo.fonte,
        "anomes": anomes,
        "status": arquivo.status,
        "raw_path": str(arquivo.raw_path),
        "mart_path": str(arquivo.mart_path),
        "linhas_raw": arquivo.linhas_raw,
        "linhas_mart": arquivo.linhas_mart,
        "erro": arquivo.erro,
    }
