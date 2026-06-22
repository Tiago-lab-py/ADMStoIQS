from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb


ROOT_DIR = Path(__file__).resolve().parents[3]
IQS_RAW_DIR = ROOT_DIR / "data" / "external" / "iqs" / "raw"
IQS_MART_DIR = ROOT_DIR / "data" / "external" / "iqs" / "mart"


IQS_RAW_SOURCES = {
    "consumidores_regional": "consumidores_regional_{anomes}.parquet",
    "consumidor_faturado_regional": "consumidor_faturado_regional_{anomes}.parquet",
    "consistencia_uc_regional": "consistencia_uc_regional_{anomes}.parquet",
    "sobreposicao_hcai": "sobreposicao_hcai_{anomes}.parquet",
}

IQS_ON_DEMAND_SOURCES = {
    "metas_uc": "metas_uc_{anomes}.parquet",
}


@dataclass(frozen=True)
class IqsMartFileResult:
    fonte: str
    raw_path: Path
    mart_path: Path
    linhas_raw: int
    linhas_mart: int
    status: str
    erro: str = ""


@dataclass(frozen=True)
class IqsMartResult:
    anomes: str
    arquivos: list[IqsMartFileResult]
    resumo_path: Path
    resumo_atual_path: Path


class IqsMartService:
    def materializar_fonte_sob_demanda(self, fonte: str, anomes: str) -> IqsMartFileResult:
        if fonte not in IQS_ON_DEMAND_SOURCES:
            raise ValueError(f"Fonte sob demanda não configurada: {fonte}")

        IQS_MART_DIR.mkdir(parents=True, exist_ok=True)
        pattern = IQS_ON_DEMAND_SOURCES[fonte]
        raw_path = self._resolve_raw_path(fonte=fonte, pattern=pattern, anomes=anomes)
        mart_path = IQS_MART_DIR / f"mart_{fonte}_{anomes}.parquet"
        return self._materializar_fonte(
            anomes=anomes,
            fonte=fonte,
            raw_path=raw_path,
            mart_path=mart_path,
        )

    def materializar(self, anomes: str) -> IqsMartResult:
        IQS_MART_DIR.mkdir(parents=True, exist_ok=True)
        arquivos: list[IqsMartFileResult] = []

        for fonte, pattern in IQS_RAW_SOURCES.items():
            raw_path = self._resolve_raw_path(fonte, pattern, anomes)
            mart_path = IQS_MART_DIR / f"mart_{fonte}_{anomes}.parquet"
            arquivos.append(self._materializar_fonte(anomes, fonte, raw_path, mart_path))

        resumo_path = IQS_MART_DIR / f"resumo_iqs_{anomes}.parquet"
        resumo_atual_path = IQS_MART_DIR / "resumo_iqs_ATUAL.parquet"
        self._materializar_resumo(anomes, arquivos, resumo_path)
        shutil.copy2(resumo_path, resumo_atual_path)

        return IqsMartResult(
            anomes=anomes,
            arquivos=arquivos,
            resumo_path=resumo_path,
            resumo_atual_path=resumo_atual_path,
        )

    def ler_resumo_atual(self) -> dict[str, Any] | None:
        resumo_path = IQS_MART_DIR / "resumo_iqs_ATUAL.parquet"
        if not resumo_path.exists():
            return None

        with duckdb.connect(database=":memory:") as connection:
            result = connection.execute("SELECT * FROM read_parquet(?)", [str(resumo_path)])
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        return {
            "arquivos": [dict(zip(columns, row)) for row in rows],
            "total_fontes": len(rows),
            "fontes_processadas": sum(1 for row in rows if dict(zip(columns, row)).get("status") == "processado"),
        }

    def _materializar_fonte(
        self,
        anomes: str,
        fonte: str,
        raw_path: Path,
        mart_path: Path,
    ) -> IqsMartFileResult:
        if not raw_path.exists():
            return IqsMartFileResult(
                fonte=fonte,
                raw_path=raw_path,
                mart_path=mart_path,
                linhas_raw=0,
                linhas_mart=0,
                status="pendente_raw",
                erro=f"Raw não encontrado: {raw_path}",
            )

    def _resolve_raw_path(self, fonte: str, pattern: str, anomes: str) -> Path:
        exact_path = IQS_RAW_DIR / pattern.format(anomes=anomes)
        if exact_path.exists():
            return exact_path

        candidates = sorted(IQS_RAW_DIR.glob(f"*{fonte}*{anomes}*.parquet"))
        if candidates:
            return candidates[-1]

        return exact_path

        try:
            with duckdb.connect(database=":memory:") as connection:
                linhas_raw = int(
                    connection.execute("SELECT count(*) FROM read_parquet(?)", [str(raw_path)]).fetchone()[0] or 0
                )
                connection.execute(
                    """
                    COPY (
                        SELECT DISTINCT
                            ? AS ANOMES_IQS_EXTRAIDO,
                            ? AS FONTE_IQS,
                            *
                        FROM read_parquet(?)
                    ) TO ? (FORMAT PARQUET)
                    """,
                    [anomes, fonte, str(raw_path), str(mart_path)],
                )
                linhas_mart = int(
                    connection.execute("SELECT count(*) FROM read_parquet(?)", [str(mart_path)]).fetchone()[0] or 0
                )

            return IqsMartFileResult(
                fonte=fonte,
                raw_path=raw_path,
                mart_path=mart_path,
                linhas_raw=linhas_raw,
                linhas_mart=linhas_mart,
                status="processado",
            )
        except Exception as exc:
            return IqsMartFileResult(
                fonte=fonte,
                raw_path=raw_path,
                mart_path=mart_path,
                linhas_raw=0,
                linhas_mart=0,
                status="erro",
                erro=f"{type(exc).__name__}: {exc}",
            )

    def _materializar_resumo(
        self,
        anomes: str,
        arquivos: list[IqsMartFileResult],
        resumo_path: Path,
    ) -> None:
        resumo_path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "anomes": anomes,
                "fonte": arquivo.fonte,
                "raw_path": str(arquivo.raw_path),
                "mart_path": str(arquivo.mart_path),
                "linhas_raw": arquivo.linhas_raw,
                "linhas_mart": arquivo.linhas_mart,
                "status": arquivo.status,
                "erro": arquivo.erro,
                "materializado_em": datetime.now().isoformat(timespec="seconds"),
            }
            for arquivo in arquivos
        ]

        with duckdb.connect(database=":memory:") as connection:
            if not rows:
                connection.execute(
                    "COPY (SELECT 'sem_fontes' AS status WHERE false) TO ? (FORMAT PARQUET)",
                    [str(resumo_path)],
                )
                return

            selects = []
            for row in rows:
                selects.append(
                    "SELECT "
                    + ", ".join(
                        [
                            self._sql_literal(row["anomes"]) + " AS anomes",
                            self._sql_literal(row["fonte"]) + " AS fonte",
                            self._sql_literal(row["raw_path"]) + " AS raw_path",
                            self._sql_literal(row["mart_path"]) + " AS mart_path",
                            str(row["linhas_raw"]) + " AS linhas_raw",
                            str(row["linhas_mart"]) + " AS linhas_mart",
                            self._sql_literal(row["status"]) + " AS status",
                            self._sql_literal(row["erro"]) + " AS erro",
                            self._sql_literal(row["materializado_em"]) + " AS materializado_em",
                        ]
                    )
                )

            connection.execute(
                f"COPY ({' UNION ALL '.join(selects)}) TO ? (FORMAT PARQUET)",
                [str(resumo_path)],
            )

    def _sql_literal(self, value: Any) -> str:
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"


# Definição final e defensiva. Mantida no fim do módulo para substituir versões
# intermediárias carregadas acima durante a evolução do serviço.
class IqsMartService:
    def materializar(self, anomes: str) -> IqsMartResult:
        IQS_MART_DIR.mkdir(parents=True, exist_ok=True)
        arquivos: list[IqsMartFileResult] = []

        for fonte, pattern in IQS_RAW_SOURCES.items():
            raw_path = self._resolve_raw_path(fonte=fonte, pattern=pattern, anomes=anomes)
            mart_path = IQS_MART_DIR / f"mart_{fonte}_{anomes}.parquet"
            arquivos.append(
                self._materializar_fonte(
                    anomes=anomes,
                    fonte=fonte,
                    raw_path=raw_path,
                    mart_path=mart_path,
                )
            )

        resumo_path = IQS_MART_DIR / f"resumo_iqs_{anomes}.parquet"
        resumo_atual_path = IQS_MART_DIR / "resumo_iqs_ATUAL.parquet"
        self._materializar_resumo(anomes=anomes, arquivos=arquivos, resumo_path=resumo_path)
        shutil.copy2(resumo_path, resumo_atual_path)

        return IqsMartResult(
            anomes=anomes,
            arquivos=arquivos,
            resumo_path=resumo_path,
            resumo_atual_path=resumo_atual_path,
        )

    def ler_resumo_atual(self) -> dict[str, Any] | None:
        resumo_path = IQS_MART_DIR / "resumo_iqs_ATUAL.parquet"
        if not resumo_path.exists():
            return None

        with duckdb.connect(database=":memory:") as connection:
            result = connection.execute("SELECT * FROM read_parquet(?)", [str(resumo_path)])
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        arquivos = [dict(zip(columns, row)) for row in rows]
        return {
            "arquivos": arquivos,
            "total_fontes": len(arquivos),
            "fontes_processadas": sum(1 for item in arquivos if item.get("status") == "processado"),
        }

    def _resolve_raw_path(self, *, fonte: str, pattern: str, anomes: str) -> Path:
        exact_path = IQS_RAW_DIR / pattern.format(anomes=anomes)
        if exact_path.exists():
            return exact_path

        candidates = sorted(IQS_RAW_DIR.glob(f"*{fonte}*{anomes}*.parquet"))
        if candidates:
            return candidates[-1]

        return exact_path

    def _materializar_fonte(
        self,
        *,
        anomes: str,
        fonte: str,
        raw_path: Path,
        mart_path: Path,
    ) -> IqsMartFileResult:
        if not raw_path.exists():
            return IqsMartFileResult(
                fonte=fonte,
                raw_path=raw_path,
                mart_path=mart_path,
                linhas_raw=0,
                linhas_mart=0,
                status="pendente_raw",
                erro=f"Raw não encontrado: {raw_path}",
            )

        try:
            with duckdb.connect(database=":memory:") as connection:
                linhas_raw = int(
                    connection.execute(
                        "SELECT count(*) FROM read_parquet(?)",
                        [str(raw_path)],
                    ).fetchone()[0]
                    or 0
                )
                connection.execute(
                    """
                    CREATE OR REPLACE TEMP TABLE mart_iqs AS
                    SELECT DISTINCT *
                    FROM read_parquet(?)
                    """,
                    [str(raw_path)],
                )
                linhas_mart = int(
                    connection.execute("SELECT count(*) FROM mart_iqs").fetchone()[0]
                    or 0
                )
                connection.execute("COPY mart_iqs TO ? (FORMAT PARQUET)", [str(mart_path)])

            return IqsMartFileResult(
                fonte=fonte,
                raw_path=raw_path,
                mart_path=mart_path,
                linhas_raw=linhas_raw,
                linhas_mart=linhas_mart,
                status="processado",
            )
        except Exception as exc:
            return IqsMartFileResult(
                fonte=fonte,
                raw_path=raw_path,
                mart_path=mart_path,
                linhas_raw=0,
                linhas_mart=0,
                status="erro",
                erro=f"{type(exc).__name__}: {exc}",
            )

    def _materializar_resumo(
        self,
        *,
        anomes: str,
        arquivos: list[IqsMartFileResult],
        resumo_path: Path,
    ) -> None:
        resumo_path.parent.mkdir(parents=True, exist_ok=True)
        selects: list[str] = []

        for arquivo in arquivos:
            selects.append(
                "SELECT "
                + ", ".join(
                    [
                        self._sql_literal(anomes) + " AS anomes",
                        self._sql_literal(arquivo.fonte) + " AS fonte",
                        self._sql_literal(str(arquivo.raw_path)) + " AS raw_path",
                        self._sql_literal(str(arquivo.mart_path)) + " AS mart_path",
                        str(arquivo.linhas_raw) + " AS linhas_raw",
                        str(arquivo.linhas_mart) + " AS linhas_mart",
                        self._sql_literal(arquivo.status) + " AS status",
                        self._sql_literal(arquivo.erro) + " AS erro",
                        self._sql_literal(datetime.now().isoformat(timespec="seconds")) + " AS materializado_em",
                    ]
                )
            )

        with duckdb.connect(database=":memory:") as connection:
            if not selects:
                connection.execute(
                    "COPY (SELECT 'sem_fontes' AS status WHERE false) TO ? (FORMAT PARQUET)",
                    [str(resumo_path)],
                )
                return

            connection.execute(
                f"COPY ({' UNION ALL '.join(selects)}) TO ? (FORMAT PARQUET)",
                [str(resumo_path)],
            )

    def _sql_literal(self, value: Any) -> str:
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"
