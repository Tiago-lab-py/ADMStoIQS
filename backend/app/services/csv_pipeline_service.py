from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import duckdb

from backend.app.core.contracts import (
    LOG_LEITURA_CSV_PATH,
    MIN_ANOMES,
    SOURCE_CSV_PATTERN,
    SOURCE_DIR,
)
from backend.app.services.csv_ingestion_service import CsvIngestionService


CSV_NAME_PATTERN = re.compile(
    r"Interrupcoes_IQS_(?P<timestamp>\d{14})_(?P<regional>[A-Za-z0-9]+)\.CSV$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CsvArquivoStatus:
    arquivo: str
    caminho: str
    anomes: str
    regional_origem: str
    tamanho_bytes: int
    modificado_em: str
    status: str


@dataclass(frozen=True)
class CsvPendenciaResumo:
    arquivos_encontrados: int
    arquivos_processados: int
    arquivos_com_erro: int
    arquivos_pendentes: int
    pendentes_por_mes: dict[str, int]
    erros_por_mes: dict[str, int]
    min_anomes: str
    arquivos: list[CsvArquivoStatus]
    aviso_log: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CsvProcessamentoResumo:
    antes: CsvPendenciaResumo
    depois: CsvPendenciaResumo
    arquivos_processados_nesta_execucao: int
    linhas_lidas: int
    linhas_deduplicadas: int
    resultados: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CsvPipelineService:
    """Orquestra a conferência operacional de CSVs pendentes.

    A tela de ETL deve mostrar somente o que ainda precisa de ação. O log
    completo continua sendo usado para contagem e governança, mas não volta
    como lista visual de arquivos processados.
    """

    def verificar_pendentes(self, anomes: str | None = None) -> CsvPendenciaResumo:
        self._ultimo_aviso_log = None
        arquivos_pasta = self._listar_arquivos_pasta(anomes)
        log_status = self._carregar_status_log()

        encontrados = len(arquivos_pasta)
        processados = 0
        com_erro = 0
        pendentes: list[CsvArquivoStatus] = []
        pendentes_por_mes: dict[str, int] = {}
        erros_por_mes: dict[str, int] = {}

        for arquivo in arquivos_pasta:
            status_log = self._status_do_log(arquivo, log_status)
            if status_log == "processado":
                processados += 1
                continue

            if status_log == "erro":
                com_erro += 1
                erros_por_mes[arquivo.anomes] = erros_por_mes.get(arquivo.anomes, 0) + 1

            pendente = CsvArquivoStatus(
                arquivo=arquivo.arquivo,
                caminho=arquivo.caminho,
                anomes=arquivo.anomes,
                regional_origem=arquivo.regional_origem,
                tamanho_bytes=arquivo.tamanho_bytes,
                modificado_em=arquivo.modificado_em,
                status="pendente",
            )
            pendentes.append(pendente)
            pendentes_por_mes[arquivo.anomes] = pendentes_por_mes.get(arquivo.anomes, 0) + 1

        pendentes.sort(key=lambda item: (item.anomes, item.regional_origem, item.arquivo))

        return CsvPendenciaResumo(
            arquivos_encontrados=encontrados,
            arquivos_processados=processados,
            arquivos_com_erro=com_erro,
            arquivos_pendentes=len(pendentes),
            pendentes_por_mes=dict(sorted(pendentes_por_mes.items())),
            erros_por_mes=dict(sorted(erros_por_mes.items())),
            min_anomes=MIN_ANOMES,
            arquivos=pendentes,
            aviso_log=self._ultimo_aviso_log,
        )

    def processar_pendentes(self, anomes: str | None = None) -> CsvProcessamentoResumo:
        antes = self.verificar_pendentes(anomes)
        summary = CsvIngestionService().process_pending(anomes=anomes)
        depois = self.verificar_pendentes(anomes)
        resultados = self._normalizar_resultados(summary)

        linhas_lidas = sum(int(item.get("linhas_lidas") or 0) for item in resultados)
        linhas_deduplicadas = sum(
            int(item.get("linhas_processadas") or item.get("linhas_deduplicadas") or 0)
            for item in resultados
        )

        return CsvProcessamentoResumo(
            antes=antes,
            depois=depois,
            arquivos_processados_nesta_execucao=max(
                antes.arquivos_pendentes - depois.arquivos_pendentes,
                0,
            ),
            linhas_lidas=linhas_lidas,
            linhas_deduplicadas=linhas_deduplicadas,
            resultados=resultados,
        )

    def verificar(self, anomes: str | None = None) -> dict[str, Any]:
        return self.verificar_pendentes(anomes).to_dict()

    def verificar_pendencias(self, anomes: str | None = None) -> dict[str, Any]:
        return self.verificar(anomes)

    def processar(self, anomes: str | None = None) -> dict[str, Any]:
        return self.processar_pendentes(anomes).to_dict()

    def processar_pendencias(self, anomes: str | None = None) -> dict[str, Any]:
        return self.processar(anomes)

    def _listar_arquivos_pasta(self, anomes: str | None) -> list[CsvArquivoStatus]:
        if not SOURCE_DIR.exists():
            raise FileNotFoundError(f"Pasta de origem não encontrada: {SOURCE_DIR}")

        arquivos: list[CsvArquivoStatus] = []
        for path in SOURCE_DIR.glob(SOURCE_CSV_PATTERN):
            if not path.is_file():
                continue

            metadata = self._metadata_arquivo(path)
            if metadata is None:
                continue
            if anomes and metadata.anomes != anomes:
                continue

            arquivos.append(metadata)

        arquivos.sort(key=lambda item: (item.anomes, item.regional_origem, item.arquivo))
        return arquivos

    def _metadata_arquivo(self, path: Path) -> CsvArquivoStatus | None:
        match = CSV_NAME_PATTERN.match(path.name)
        if not match:
            return None

        stat = path.stat()
        timestamp = match.group("timestamp")
        return CsvArquivoStatus(
            arquivo=path.name,
            caminho=str(path),
            anomes=timestamp[:6],
            regional_origem=match.group("regional").upper(),
            tamanho_bytes=int(stat.st_size),
            modificado_em=self._formatar_timestamp(stat.st_mtime),
            status="pendente",
        )

    def _carregar_status_log(self) -> dict[str, str]:
        if not LOG_LEITURA_CSV_PATH.exists():
            return {}

        query = """
            SELECT
                lower(trim(COALESCE(CAST(arquivo_path AS VARCHAR), ''))) AS arquivo_path,
                lower(trim(COALESCE(CAST(arquivo_nome AS VARCHAR), ''))) AS arquivo_nome,
                lower(trim(COALESCE(CAST(status AS VARCHAR), ''))) AS status,
                COALESCE(CAST(processado_em AS VARCHAR), '') AS processado_em
            FROM read_parquet(?)
            ORDER BY COALESCE(CAST(processado_em AS VARCHAR), '')
        """

        status_por_chave: dict[str, str] = {}
        try:
            with duckdb.connect(database=":memory:") as connection:
                rows = connection.execute(query, [str(LOG_LEITURA_CSV_PATH)]).fetchall()
        except Exception as exc:
            self._ultimo_aviso_log = (
                f"Falha ao ler {LOG_LEITURA_CSV_PATH}. "
                f"A comparação usou somente a pasta. Erro original: {exc}"
            )
            return {}

        for arquivo_path, arquivo_nome, status, _processado_em in rows:
            status_normalizado = status or ""
            if arquivo_path:
                status_por_chave[self._normalizar_caminho(arquivo_path)] = status_normalizado
            if arquivo_nome:
                status_por_chave[self._normalizar_nome(arquivo_nome)] = status_normalizado

        return status_por_chave

    def _status_do_log(
        self,
        arquivo: CsvArquivoStatus,
        log_status: dict[str, str],
    ) -> str:
        caminho = self._normalizar_caminho(arquivo.caminho)
        nome = self._normalizar_nome(arquivo.arquivo)
        return log_status.get(caminho) or log_status.get(nome) or "pendente"

    def _normalizar_caminho(self, value: str) -> str:
        return value.replace("/", "\\").strip().lower()

    def _normalizar_nome(self, value: str) -> str:
        return Path(value.strip()).name.lower()

    def _formatar_timestamp(self, timestamp: float) -> str:
        from datetime import datetime

        return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")

    def _normalizar_resultados(self, summary: Any) -> list[dict[str, Any]]:
        if summary is None:
            return []

        if hasattr(summary, "results"):
            values = getattr(summary, "results") or []
        elif hasattr(summary, "resultados"):
            values = getattr(summary, "resultados") or []
        elif isinstance(summary, dict):
            values = summary.get("results") or summary.get("resultados") or []
        else:
            values = []

        normalized: list[dict[str, Any]] = []
        for item in values:
            if hasattr(item, "__dataclass_fields__"):
                normalized.append(asdict(item))
            elif isinstance(item, dict):
                normalized.append(dict(item))
            else:
                normalized.append(
                    {
                        key: value
                        for key, value in vars(item).items()
                        if not key.startswith("_")
                    }
                )
        return normalized
