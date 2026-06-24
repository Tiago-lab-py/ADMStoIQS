from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from backend.app.core.contracts import LOGS_DIR
from backend.app.services.csv_pipeline_service import CsvPipelineService
from backend.app.services.etl_apuracao_service import EtlApuracaoService
from backend.app.services.indicadores_continuidade_service import IndicadoresContinuidadeService
from backend.app.services.oms_union_service import OmsUnionService
from backend.app.services.pendencias_apuracao_service import PendenciasApuracaoService
from backend.app.services.ressarcimento_service_v2 import RessarcimentoService
from backend.app.services.sobreposicao_interrupcao_service import SobreposicaoInterrupcaoService
from backend.app.services.tratamento_massivo_service import TratamentoMassivoService


ORQUESTRADOR_LOG_PATH = LOGS_DIR / "log_orquestrador_apuracao.parquet"


@dataclass
class OrquestradorEtapa:
    etapa: str
    status: str
    mensagem: str
    iniciado_em: str
    finalizado_em: str | None = None
    detalhes: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrquestradorApuracaoResult:
    anomes: str
    status: str
    usuario: str
    perfil: str
    iniciado_em: str
    finalizado_em: str
    etapas: list[OrquestradorEtapa]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["etapas"] = [asdict(etapa) for etapa in self.etapas]
        return payload


class OrquestradorApuracaoService:
    """Executa a trilha operacional diária/mensal em uma sequência única.

    A intenção é que agendador, terminal e frontend admin chamem o mesmo fluxo,
    evitando divergência entre "o que roda no script" e "o que a tela mostra".
    """

    def executar(
        self,
        *,
        anomes: str,
        usuario: str = "SISTEMA_AI",
        perfil: str = "sistema",
        processar_csv: bool = True,
        atualizar_union: bool = True,
        gerar_apuracao: bool = True,
        materializar_pendencias: bool = True,
        materializar_sobreposicao_interrupcao: bool = True,
        gerar_tratado: bool = True,
        materializar_indicadores: bool = True,
        materializar_ressarcimento: bool = True,
        remover_canceladas: bool = True,
    ) -> OrquestradorApuracaoResult:
        anomes = self._normalizar_anomes(anomes)
        iniciado_em = self._agora()
        etapas: list[OrquestradorEtapa] = []

        def run(etapa: str, mensagem: str, action):
            registro = OrquestradorEtapa(
                etapa=etapa,
                status="processando",
                mensagem=mensagem,
                iniciado_em=self._agora(),
            )
            etapas.append(registro)
            self._registrar_log(anomes, usuario, perfil, registro)
            try:
                result = action()
                registro.status = "sucesso"
                registro.finalizado_em = self._agora()
                registro.detalhes = self._normalizar_detalhes(result)
                registro.mensagem = f"{mensagem} Concluído."
                self._registrar_log(anomes, usuario, perfil, registro)
                return result
            except Exception as exc:
                registro.status = "erro"
                registro.finalizado_em = self._agora()
                registro.mensagem = f"{mensagem} Erro: {exc}"
                registro.detalhes = {"erro": repr(exc)}
                self._registrar_log(anomes, usuario, perfil, registro)
                raise

        if processar_csv:
            run(
                "csv_pendentes",
                "Processando CSVs pendentes da pasta de origem.",
                lambda: CsvPipelineService().processar(anomes=None),
            )

        if atualizar_union:
            run(
                "oms_union",
                "Atualizando mart consolidado OMS UNION.",
                lambda: OmsUnionService().build(),
            )

        if gerar_apuracao:
            run(
                "apuracao_mensal",
                "Gerando apuração mensal.",
                lambda: EtlApuracaoService().executar(
                    anomes=anomes,
                    remover_canceladas=remover_canceladas,
                ),
            )

        if materializar_pendencias:
            run(
                "pendencias",
                "Materializando pendências da apuração.",
                lambda: PendenciasApuracaoService().materializar(anomes),
            )

        if materializar_sobreposicao_interrupcao:
            run(
                "sobreposicao_interrupcao",
                "Materializando análise de sobreposição por interrupção/equipamento.",
                lambda: SobreposicaoInterrupcaoService().materializar(anomes),
            )

        if gerar_tratado:
            run(
                "tratamento_massivo",
                "Gerando base tratada para indicadores e exportação.",
                lambda: TratamentoMassivoService().gerar_apuracao_tratada(anomes),
            )

        if materializar_indicadores:
            run(
                "indicadores_continuidade",
                "Materializando DEC/FEC/DIC/FIC/DMIC.",
                lambda: IndicadoresContinuidadeService().materializar(anomes),
            )

        if materializar_ressarcimento:
            run(
                "ressarcimento",
                "Materializando ressarcimento estimado.",
                lambda: RessarcimentoService().materializar(anomes),
            )

        finalizado_em = self._agora()
        status = "processado" if all(etapa.status == "sucesso" for etapa in etapas) else "parcial"
        return OrquestradorApuracaoResult(
            anomes=anomes,
            status=status,
            usuario=usuario,
            perfil=perfil,
            iniciado_em=iniciado_em,
            finalizado_em=finalizado_em,
            etapas=etapas,
        )

    def _normalizar_anomes(self, anomes: str) -> str:
        value = str(anomes).strip()
        if len(value) != 6 or not value.isdigit():
            raise ValueError("Mês de apuração inválido. Use AAAAMM.")
        return value

    def _agora(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _normalizar_detalhes(self, result: Any) -> dict[str, Any]:
        if result is None:
            return {}
        if hasattr(result, "to_dict"):
            return result.to_dict()
        if hasattr(result, "__dict__"):
            return {
                key: self._serializar_valor(value)
                for key, value in vars(result).items()
                if not key.startswith("_")
            }
        if isinstance(result, dict):
            return {str(key): self._serializar_valor(value) for key, value in result.items()}
        return {"resultado": self._serializar_valor(result)}

    def _serializar_valor(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return [self._serializar_valor(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._serializar_valor(item) for key, item in value.items()}
        return str(value)

    def _registrar_log(
        self,
        anomes: str,
        usuario: str,
        perfil: str,
        etapa: OrquestradorEtapa,
    ) -> None:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "anomes": anomes,
            "usuario": usuario,
            "perfil": perfil,
            "etapa": etapa.etapa,
            "status": etapa.status,
            "mensagem": etapa.mensagem,
            "iniciado_em": etapa.iniciado_em,
            "finalizado_em": etapa.finalizado_em or "",
            "detalhes": str(etapa.detalhes),
            "registrado_em": self._agora(),
        }
        incoming = pd.DataFrame([record])
        if ORQUESTRADOR_LOG_PATH.exists():
            current = pd.read_parquet(ORQUESTRADOR_LOG_PATH)
            incoming = pd.concat([current, incoming], ignore_index=True)
        incoming.to_parquet(ORQUESTRADOR_LOG_PATH, index=False)
