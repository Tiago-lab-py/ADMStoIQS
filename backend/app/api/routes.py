from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from backend.app.core.auth import (
    AuthUser,
    authenticate_user,
    create_access_token,
    get_current_user,
    request_ip,
    require_roles,
)
from backend.app.core.contracts import EXPORTS_DIR
from backend.app.schemas.api_models import (
    AlteracaoRequest,
    AlteracaoResponse,
    AmostraResponse,
    CompetenciaResponse,
    CompetenciasResponse,
    DadosResponse,
    ExportCsvRequest,
    ExportCsvResponse,
    ExportTodasRegionaisResponse,
    HealthResponse,
    LoginRequest,
    LoginResponse,
    OmsCorrigidoResponse,
    TratamentoResponse,
    UserResponse,
)
from backend.app.services.alteracao_service import AlteracaoService
from backend.app.services.oms_correcoes_service import OmsCorrecoesService
from backend.app.services.processed_data_service import ProcessedDataService
from backend.app.services.tratamento_service import TratamentoService


router = APIRouter()


@router.get("/")
def root():
    return {
        "nome": "ADMStoIQS API",
        "status": "ok",
        "docs": "/docs",
        "frontend": "http://127.0.0.1:5173",
    }


@router.get("/competencias")
def listar_competencias_mart():
    return ProcessedDataService().list_competencias()


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@router.get("/mart/dados")
def consultar_mart_dados(limit: str = "100", offset: str = "0"):
    return ProcessedDataService().get_mart_data(
        limit=_safe_int(limit, 100),
        offset=_safe_int(offset, 0),
    )


@router.get("/mart/resumo")
def consultar_mart_resumo():
    return ProcessedDataService().get_mart_resumo()


@router.get("/mart/amostra")
def gerar_mart_amostra(limit: str = "100"):
    return ProcessedDataService().get_mart_top_duracao_sample(
        limit=_safe_int(limit, 100)
    )


@router.post("/mart/exportar-csv")
def exportar_mart_csv(request: ExportCsvRequest):
    return ProcessedDataService().export_mart_csv(request)


@router.post("/mart/exportar-csv-regionais")
def exportar_mart_csv_regionais(request: ExportCsvRequest):
    return ProcessedDataService().export_mart_all_regionais(request)


@router.post("/etl/apuracao")
def executar_etl_apuracao(payload: dict[str, Any]):
    from backend.app.services.etl_apuracao_service import EtlApuracaoService
    from fastapi import HTTPException

    try:
        anomes = str(payload.get("anomes") or payload.get("mes_apuracao") or "")
        remover_rejeitados = bool(payload.get("remover_rejeitados", True))
        return EtlApuracaoService().executar(
            anomes=anomes,
            remover_rejeitados=remover_rejeitados,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao executar ETL de apuração: {error}",
        ) from error


@router.post("/etl/oms-union")
def executar_etl_oms_union():
    from contextlib import redirect_stdout
    from fastapi import HTTPException
    from io import StringIO

    try:
        from backend.scripts.gerar_oms_union import main as gerar_oms_union_main

        output = StringIO()
        with redirect_stdout(output):
            gerar_oms_union_main()
        return {
            "status": "ok",
            "mensagem": "Mart UNION gerado com sucesso.",
            "log": output.getvalue(),
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao gerar mart UNION: {error}",
        ) from error


@router.get("/etl/csv/verificar")
def verificar_csv_pendente(anomes: str | None = None):
    from fastapi import HTTPException
    from backend.app.services.csv_pipeline_service import CsvPipelineService

    try:
        return CsvPipelineService().verificar_pendencias(anomes=anomes)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao verificar CSV pendente: {error}",
        ) from error


@router.post("/etl/csv/processar")
def processar_csv_pendente(payload: dict[str, Any] | None = None):
    from fastapi import HTTPException
    from backend.app.services.csv_pipeline_service import CsvPipelineService

    try:
        body = payload or {}
        anomes = body.get("anomes")
        return CsvPipelineService().processar_pendentes(
            anomes=str(anomes) if anomes else None
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao processar CSV pendente: {error}",
        ) from error


def _decision_context(
    request: Request,
    payload: dict[str, Any] | None,
) -> tuple[str, str, str, str, str]:
    body = payload or {}
    usuario = str(body.get("usuario") or body.get("user") or "sistema")
    perfil = str(body.get("perfil") or body.get("profile") or "usuario")
    justificativa = str(body.get("justificativa") or body.get("motivo") or "")
    ip = request.client.host if request.client else ""
    pc = str(body.get("pc") or body.get("host") or request.headers.get("x-workstation") or "")
    return usuario, perfil, justificativa, ip, pc


@router.post("/registros/{chave_registro:path}/validar")
def validar_registro(
    chave_registro: str,
    request: Request,
    payload: dict[str, Any] | None = None,
):
    from backend.app.services.governance_service import GovernanceService

    usuario, perfil, justificativa, ip, pc = _decision_context(request, payload)
    if not justificativa:
        justificativa = "Registro validado pelo analista."
    return GovernanceService().validar_registro(
        chave_registro=chave_registro,
        usuario=usuario,
        perfil=perfil,
        justificativa=justificativa,
        ip=ip,
        pc=pc,
    )


@router.post("/registros/{chave_registro:path}/rejeitar")
def rejeitar_registro(
    chave_registro: str,
    request: Request,
    payload: dict[str, Any] | None = None,
):
    from backend.app.services.governance_service import GovernanceService

    usuario, perfil, justificativa, ip, pc = _decision_context(request, payload)
    if not justificativa:
        justificativa = "Registro rejeitado pelo analista."
    return GovernanceService().rejeitar_registro(
        chave_registro=chave_registro,
        usuario=usuario,
        perfil=perfil,
        justificativa=justificativa,
        ip=ip,
        pc=pc,
    )


@router.post("/registros/{chave_registro:path}/ignorar-regra")
def ignorar_regra_registro(
    chave_registro: str,
    request: Request,
    payload: dict[str, Any] | None = None,
):
    from backend.app.services.governance_service import GovernanceService

    usuario, perfil, justificativa, ip, pc = _decision_context(request, payload)
    if not justificativa:
        justificativa = "Regra automática ignorada pelo analista."
    return GovernanceService().ignorar_regra(
        chave_registro=chave_registro,
        usuario=usuario,
        perfil=perfil,
        justificativa=justificativa,
        ip=ip,
        pc=pc,
    )


@router.post("/alteracoes/{id_alteracao}/aprovar")
def aprovar_alteracao(
    id_alteracao: str,
    request: Request,
    payload: dict[str, Any] | None = None,
):
    from backend.app.services.governance_service import GovernanceService

    usuario, perfil, justificativa, ip, pc = _decision_context(request, payload)
    if not justificativa:
        justificativa = "Alteração aprovada."
    return GovernanceService().aprovar_alteracao(
        id_alteracao=id_alteracao,
        usuario=usuario,
        perfil=perfil,
        justificativa=justificativa,
        ip=ip,
        pc=pc,
    )


@router.post("/alteracoes/{id_alteracao}/rejeitar")
def rejeitar_alteracao(
    id_alteracao: str,
    request: Request,
    payload: dict[str, Any] | None = None,
):
    from backend.app.services.governance_service import GovernanceService

    usuario, perfil, justificativa, ip, pc = _decision_context(request, payload)
    if not justificativa:
        justificativa = "Alteração rejeitada."
    return GovernanceService().rejeitar_alteracao(
        id_alteracao=id_alteracao,
        usuario=usuario,
        perfil=perfil,
        justificativa=justificativa,
        ip=ip,
        pc=pc,
    )
data_service = ProcessedDataService()
alteracao_service = AlteracaoService()
tratamento_service = TratamentoService()
oms_correcoes_service = OmsCorrecoesService()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    user = authenticate_user(request.usuario, request.senha)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")

    token = create_access_token(user)
    return LoginResponse(
        access_token=token,
        usuario=user.usuario,
        nome_usuario=user.nome_usuario,
        perfil=user.perfil,
    )


@router.get("/auth/me", response_model=UserResponse)
def me(user: AuthUser = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        usuario=user.usuario,
        nome_usuario=user.nome_usuario,
        perfil=user.perfil,
    )


@router.get("/competencias", response_model=CompetenciasResponse)
def listar_competencias(
    user: AuthUser = Depends(get_current_user),
) -> CompetenciasResponse:
    _ = user
    try:
        competencias = [
            CompetenciaResponse(
                anomes=competencia.anomes,
                arquivo=competencia.path.name,
                caminho=str(competencia.path),
                tamanho_bytes=competencia.size_bytes,
                modificado_em=competencia.modified_at,
                fonte="mart",
            )
            for competencia in data_service.list_competencias()
        ]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CompetenciasResponse(competencias=competencias)


@router.get("/competencias/{anomes}/dados", response_model=DadosResponse)
def consultar_dados(
    anomes: str,
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    user: AuthUser = Depends(get_current_user),
) -> DadosResponse:
    _ = user
    try:
        records = data_service.get_data(anomes=anomes, limit=limit, offset=offset)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DadosResponse(
        anomes=anomes,
        limit=limit,
        offset=offset,
        total_retornado=len(records),
        registros=records,
    )


@router.get("/competencias/{anomes}/amostra", response_model=AmostraResponse)
def gerar_amostra(
    anomes: str,
    por_grupo: int = Query(default=100, ge=1, le=1000),
    user: AuthUser = Depends(get_current_user),
) -> AmostraResponse:
    _ = user
    try:
        records = data_service.get_top_duracao_sample(anomes=anomes, per_group=por_grupo)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AmostraResponse(
        anomes=anomes,
        criterio=f"{por_grupo} maiores durações por PID_INTRP_CONJTO_PIN",
        total_retornado=len(records),
        registros=records,
    )


@router.post("/competencias/{anomes}/exportar-csv", response_model=ExportCsvResponse)
def exportar_csv(
    anomes: str,
    request: ExportCsvRequest | None = None,
    user: AuthUser = Depends(require_roles("admin", "gestor")),
) -> ExportCsvResponse:
    _ = (request, user)
    try:
        result = data_service.export_csv(
            anomes=anomes,
            regional_origem=request.regional_origem if request else None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ExportCsvResponse(
        anomes=result.anomes,
        regional_origem=result.regional_origem,
        arquivo=result.path.name,
        caminho=str(result.path),
        tamanho_bytes=result.size_bytes,
        total_linhas=result.total_rows,
        colunas=result.total_columns,
    )


@router.post(
    "/competencias/{anomes}/exportar-csv-regionais",
    response_model=ExportTodasRegionaisResponse,
)
def exportar_csv_todas_regionais(
    anomes: str,
    request: ExportCsvRequest | None = None,
    user: AuthUser = Depends(require_roles("admin", "gestor")),
) -> ExportTodasRegionaisResponse:
    _ = (request, user)
    try:
        results = data_service.export_all_regionais(anomes=anomes)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    exports = [
        ExportCsvResponse(
            anomes=result.anomes,
            regional_origem=result.regional_origem,
            arquivo=result.path.name,
            caminho=str(result.path),
            tamanho_bytes=result.size_bytes,
            total_linhas=result.total_rows,
            colunas=result.total_columns,
        )
        for result in results
    ]
    return ExportTodasRegionaisResponse(
        anomes=anomes,
        total_regionais=len(exports),
        exports=exports,
    )


@router.get("/exports/{arquivo}")
def baixar_export(
    arquivo: str,
    user: AuthUser = Depends(get_current_user),
) -> FileResponse:
    _ = user
    if Path(arquivo).name != arquivo:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")

    path = EXPORTS_DIR / arquivo
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo exportado não encontrado.")

    return FileResponse(
        path=path,
        filename=arquivo,
        media_type="text/csv",
    )


@router.get("/tratamentos/horario-negativo", response_model=TratamentoResponse)
def tratamento_horario_negativo(
    anomes: str | None = None,
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    user: AuthUser = Depends(get_current_user),
) -> TratamentoResponse:
    _ = user
    try:
        records = tratamento_service.horario_negativo(
            anomes=anomes,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao consultar horário negativo: {type(exc).__name__}: {exc}",
        ) from exc

    return TratamentoResponse(
        tipo="horario_negativo",
        anomes=anomes,
        limit=limit,
        offset=offset,
        total_retornado=len(records),
        registros=records,
    )


@router.get("/tratamentos/sobreposicao-interrupcao", response_model=TratamentoResponse)
def tratamento_sobreposicao_interrupcao(
    anomes: str | None = None,
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    user: AuthUser = Depends(get_current_user),
) -> TratamentoResponse:
    _ = user
    try:
        records = tratamento_service.sobreposicao_interrupcao(
            anomes=anomes,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao consultar sobreposição de interrupção: {type(exc).__name__}: {exc}",
        ) from exc

    return TratamentoResponse(
        tipo="sobreposicao_interrupcao",
        anomes=anomes,
        limit=limit,
        offset=offset,
        total_retornado=len(records),
        registros=records,
    )


@router.get("/tratamentos/sobreposicao-uc", response_model=TratamentoResponse)
def tratamento_sobreposicao_uc(
    anomes: str | None = None,
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    user: AuthUser = Depends(get_current_user),
) -> TratamentoResponse:
    _ = user
    try:
        records = tratamento_service.sobreposicao_uc(
            anomes=anomes,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao consultar sobreposição de UC: {type(exc).__name__}: {exc}",
        ) from exc

    return TratamentoResponse(
        tipo="sobreposicao_uc",
        anomes=anomes,
        limit=limit,
        offset=offset,
        total_retornado=len(records),
        registros=records,
    )


@router.get("/tratamentos/sem-causa-componente", response_model=TratamentoResponse)
def tratamento_sem_causa_componente(
    anomes: str | None = None,
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    user: AuthUser = Depends(get_current_user),
) -> TratamentoResponse:
    _ = user
    try:
        records = tratamento_service.sem_causa_componente(
            anomes=anomes,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao consultar causa/componente: {type(exc).__name__}: {exc}",
        ) from exc

    return TratamentoResponse(
        tipo="sem_causa_componente",
        anomes=anomes,
        limit=limit,
        offset=offset,
        total_retornado=len(records),
        registros=records,
    )


@router.post("/alteracoes", response_model=AlteracaoResponse)
def solicitar_alteracao(
    body: AlteracaoRequest,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> AlteracaoResponse:
    record = alteracao_service.solicitar(
        request=body,
        user=user,
        ip_origem=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        hostname_origem=request.headers.get("x-hostname-origem"),
    )
    return AlteracaoResponse(
        id_alteracao=record.id_alteracao,
        status=record.status,
        usuario=record.usuario,
        anomes=record.anomes,
        chave_registro=record.chave_registro,
        campo=record.campo or "",
    )


@router.post("/mart/oms-corrigido", response_model=OmsCorrigidoResponse)
def gerar_oms_corrigido(
    user: AuthUser = Depends(require_roles("admin", "gestor")),
) -> OmsCorrigidoResponse:
    _ = user
    try:
        result = oms_correcoes_service.aplicar()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return OmsCorrigidoResponse(
        alteracoes_aplicadas=result.alteracoes_aplicadas,
        linhas_saida=result.linhas_saida,
        parquet_path=str(result.parquet_path),
    )
from typing import Any

from fastapi import Body, Request
