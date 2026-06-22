from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class LoginRequest(BaseModel):
    usuario: str
    senha: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: str
    nome_usuario: str
    perfil: str


class UserResponse(BaseModel):
    usuario: str
    nome_usuario: str
    perfil: str


class CompetenciaResponse(BaseModel):
    anomes: str
    arquivo: str
    caminho: str
    tamanho_bytes: int
    modificado_em: datetime
    fonte: str


class CompetenciasResponse(BaseModel):
    competencias: list[CompetenciaResponse]


class DadosResponse(BaseModel):
    anomes: str
    limit: int
    offset: int
    total_retornado: int
    registros: list[dict[str, object | None]]


class TratamentoResponse(BaseModel):
    tipo: str
    anomes: str | None
    limit: int
    offset: int
    total_retornado: int
    registros: list[dict[str, object | None]]


class AmostraResponse(BaseModel):
    anomes: str
    criterio: str
    total_retornado: int
    registros: list[dict[str, object | None]]


class ExportCsvRequest(BaseModel):
    usuario: str | None = Field(
        default=None,
        description="Usuário solicitante. Será obrigatório quando a governança completa for implementada.",
    )
    regional_origem: str | None = Field(
        default=None,
        description="Filtra a exportação por regional de origem, como CSL, LES, NRO, NRT ou OES.",
    )
    justificativa: str | None = Field(
        default=None,
        description="Justificativa da geração do CSV.",
    )


class ExportCsvResponse(BaseModel):
    anomes: str
    regional_origem: str | None
    arquivo: str
    caminho: str
    tamanho_bytes: int
    total_linhas: int
    colunas: int


class ExportTodasRegionaisResponse(BaseModel):
    anomes: str
    total_regionais: int
    exports: list[ExportCsvResponse]


class OmsCorrigidoResponse(BaseModel):
    alteracoes_aplicadas: int
    linhas_saida: int
    parquet_path: str


class ErrorResponse(BaseModel):
    detail: str


class AlteracaoRequest(BaseModel):
    anomes: str
    chave_registro: str
    campo: str
    valor_anterior: str | None = None
    valor_novo: str
    justificativa: str


class AlteracaoResponse(BaseModel):
    id_alteracao: str
    status: str
    usuario: str
    anomes: str
    chave_registro: str
    campo: str


def path_to_response_path(path: Path) -> str:
    return str(path)
