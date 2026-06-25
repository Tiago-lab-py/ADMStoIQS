from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

DATE_COLUMNS = {
    "DATA_HORA_INIC_INTRP_TS": "DATA_HORA_INIC_INTRP",
    "DATA_HORA_FIM_INTRP_TS": "DATA_HORA_FIM_INTRP",
    "DTHR_INICIO_INTRP_UC_TS": "DTHR_INICIO_INTRP_UC",
}


@dataclass(frozen=True)
class NormalizacaoResult:
    arquivo: Path
    status: str
    linhas: int
    colunas_adicionadas: tuple[str, ...]
    mensagem: str


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Adiciona colunas TIMESTAMP derivadas aos Parquets mensais já processados, "
            "sem reler os CSVs de origem."
        )
    )
    parser.add_argument(
        "--anomes",
        default=None,
        help="Competência específica no formato YYYYMM. Se omitido, processa todos.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recria as colunas _TS mesmo quando elas já existem.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Cria uma cópia .bak antes de substituir o Parquet. Desligado por padrão para evitar arquivos grandes.",
    )
    args = parser.parse_args()

    arquivos = _listar_arquivos(args.anomes)
    if not arquivos:
        filtro = f" para {args.anomes}" if args.anomes else ""
        print(f"[Datas] Nenhum Parquet mensal encontrado{filtro} em {PROCESSED_DIR}.")
        return

    print("[Datas] Normalizando datas dos Parquets processados...")
    print(f"[Datas] Diretório: {PROCESSED_DIR}")
    print(f"[Datas] Arquivos encontrados: {len(arquivos)}")
    print(f"[Datas] Backup completo: {'sim' if args.backup else 'não'}")
    print(f"[Datas] Recriar colunas existentes: {'sim' if args.force else 'não'}")

    resultados: list[NormalizacaoResult] = []
    for indice, arquivo in enumerate(arquivos, start=1):
        print(f"[Datas] Arquivo {indice} de {len(arquivos)} | {arquivo.name}")
        resultado = normalizar_arquivo(arquivo, force=args.force, backup=args.backup)
        resultados.append(resultado)
        adicionadas = ", ".join(resultado.colunas_adicionadas) or "-"
        print(
            f"[Datas] {resultado.status.upper()} | linhas={resultado.linhas} | "
            f"colunas={adicionadas} | {resultado.mensagem}"
        )

    atualizados = sum(1 for item in resultados if item.status == "atualizado")
    ignorados = sum(1 for item in resultados if item.status == "ignorado")
    erros = sum(1 for item in resultados if item.status == "erro")

    print("[Datas] Normalização concluída.")
    print(f"[Datas] Atualizados: {atualizados}")
    print(f"[Datas] Ignorados: {ignorados}")
    print(f"[Datas] Erros: {erros}")
    print("[Datas] Próximo passo recomendado: python -m backend.scripts.gerar_oms_union")


def normalizar_arquivo(arquivo: Path, force: bool = False, backup: bool = False) -> NormalizacaoResult:
    temp_path = arquivo.with_name(f"{arquivo.stem}.datas_ts.tmp.parquet")
    backup_path = arquivo.with_suffix(f"{arquivo.suffix}.bak")

    try:
        with duckdb.connect(database=":memory:") as connection:
            colunas = _colunas_parquet(connection, arquivo)
            faltantes = tuple(coluna for coluna in DATE_COLUMNS if force or coluna not in colunas)
            linhas = _contar_linhas(connection, arquivo)

            if not faltantes:
                return NormalizacaoResult(
                    arquivo=arquivo,
                    status="ignorado",
                    linhas=linhas,
                    colunas_adicionadas=(),
                    mensagem="colunas _TS já existem",
                )

            origem_ausente = [
                origem
                for coluna_ts, origem in DATE_COLUMNS.items()
                if coluna_ts in faltantes and origem not in colunas
            ]
            if origem_ausente:
                return NormalizacaoResult(
                    arquivo=arquivo,
                    status="erro",
                    linhas=linhas,
                    colunas_adicionadas=faltantes,
                    mensagem="colunas de origem ausentes: " + ", ".join(origem_ausente),
                )

            if temp_path.exists():
                temp_path.unlink()

            select_parts = []
            for coluna in colunas:
                if force and coluna in DATE_COLUMNS:
                    continue
                select_parts.append(_quote_identifier(coluna))
            for coluna_ts in faltantes:
                select_parts.append(f"{_timestamp_expr(DATE_COLUMNS[coluna_ts])} AS {_quote_identifier(coluna_ts)}")

            select_sql = ",\n                    ".join(select_parts)
            connection.execute(
                f"""
                COPY (
                    SELECT
                        {select_sql}
                    FROM read_parquet(?)
                )
                TO ? (
                    FORMAT PARQUET,
                    COMPRESSION ZSTD
                )
                """,
                [str(arquivo), str(temp_path)],
            )

            linhas_temp = _contar_linhas(connection, temp_path)
            if linhas_temp != linhas:
                temp_path.unlink(missing_ok=True)
                return NormalizacaoResult(
                    arquivo=arquivo,
                    status="erro",
                    linhas=linhas,
                    colunas_adicionadas=faltantes,
                    mensagem=f"contagem divergente após regravação: {linhas_temp}",
                )

        if backup:
            if backup_path.exists():
                backup_path.unlink()
            os.replace(arquivo, backup_path)
        os.replace(temp_path, arquivo)

        return NormalizacaoResult(
            arquivo=arquivo,
            status="atualizado",
            linhas=linhas,
            colunas_adicionadas=faltantes,
            mensagem="parquet regravado com timestamps derivados",
        )
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        return NormalizacaoResult(
            arquivo=arquivo,
            status="erro",
            linhas=0,
            colunas_adicionadas=(),
            mensagem=str(exc),
        )


def _listar_arquivos(anomes: str | None) -> list[Path]:
    if anomes:
        return sorted(PROCESSED_DIR.glob(f"agrupamento_oms_{anomes}.parquet"))
    return sorted(PROCESSED_DIR.glob("agrupamento_oms_*.parquet"))


def _colunas_parquet(connection: duckdb.DuckDBPyConnection, arquivo: Path) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(arquivo)],
        ).fetchall()
    ]


def _contar_linhas(connection: duckdb.DuckDBPyConnection, arquivo: Path) -> int:
    return int(
        connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(arquivo)],
        ).fetchone()[0]
    )


def _timestamp_expr(coluna: str) -> str:
    quoted = _quote_identifier(coluna)
    return f"""
        COALESCE(
            TRY_STRPTIME(NULLIF(CAST({quoted} AS VARCHAR), ''), '%d/%m/%Y %H:%M:%S'),
            TRY_STRPTIME(NULLIF(CAST({quoted} AS VARCHAR), ''), '%Y-%m-%d %H:%M:%S'),
            TRY_CAST(NULLIF(CAST({quoted} AS VARCHAR), '') AS TIMESTAMP)
        )
    """.strip()


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


if __name__ == "__main__":
    main()
