from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _request_json(url: str, method: str = "GET", timeout: int = 600) -> tuple[int, dict[str, Any]]:
    request = Request(url=url, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body or "{}")
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"detail": body}
        return error.code, payload
    except URLError as error:
        raise RuntimeError(
            f"Nao foi possivel acessar a API em {url}. "
            "Confirme se `python -m backend.scripts.run_api` esta rodando."
        ) from error


def _print_json(title: str, payload: dict[str, Any]) -> None:
    print(title)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _validar_resumo_iqs(base_url: str, anomes: str) -> bool:
    url = f"{base_url}/iqs/resumo?refresh=true&anomes={anomes}"
    print(f"[1/3] Validando IQS: {url}")
    status_code, payload = _request_json(url)
    _print_json("[IQS] Resposta:", payload)

    if status_code >= 400:
        print(f"[IQS] ERRO HTTP {status_code}.")
        return False

    arquivos = payload.get("arquivos", [])
    erros = [item for item in arquivos if item.get("status") == "erro"]
    processados = [item for item in arquivos if item.get("status") == "processado"]
    pendentes_raw = [item for item in arquivos if item.get("status") == "pendente_raw"]

    print("[IQS] Diagnostico:")
    print(f"  Fontes processadas: {len(processados)}")
    print(f"  Fontes pendentes raw: {len(pendentes_raw)}")
    print(f"  Fontes com erro: {len(erros)}")

    if erros:
        print("[IQS] Falhou: existem fontes com status=erro.")
        return False

    if not processados:
        print("[IQS] Falhou: nenhuma fonte foi materializada.")
        return False

    print("[IQS] OK: resumo atualizado sem erro.")
    return True


def _materializar_pendencias(base_url: str, anomes: str) -> bool:
    url = f"{base_url}/apuracao/pendencias/materializar/{anomes}"
    print(f"[2/3] Materializando pendencias: {url}")
    status_code, payload = _request_json(url, method="POST", timeout=1800)
    _print_json("[Pendencias] Resposta materializacao:", payload)

    if status_code >= 400:
        print(f"[Pendencias] ERRO HTTP {status_code}.")
        return False

    print("[Pendencias] OK: materializacao concluida.")
    return True


def _validar_resumo_pendencias(base_url: str) -> bool:
    url = f"{base_url}/apuracao/pendencias/resumo"
    print(f"[3/3] Validando resumo de pendencias: {url}")
    status_code, payload = _request_json(url)
    _print_json("[Pendencias] Resumo:", payload)

    if status_code >= 400:
        print(f"[Pendencias] ERRO HTTP {status_code}.")
        return False

    print("[Pendencias] OK: resumo disponivel.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Valida a retomada IQS e, opcionalmente, materializa pendencias da apuracao."
    )
    parser.add_argument("--anomes", default="202605", help="Competencia da apuracao, exemplo 202605.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="URL base da API local.")
    parser.add_argument(
        "--materializar-pendencias",
        action="store_true",
        help="Depois do IQS OK, executa a materializacao das pendencias.",
    )
    args = parser.parse_args()

    try:
        iqs_ok = _validar_resumo_iqs(args.base_url.rstrip("/"), args.anomes)
        if not iqs_ok:
            sys.exit(1)

        if args.materializar_pendencias:
            pendencias_ok = _materializar_pendencias(args.base_url.rstrip("/"), args.anomes)
            if not pendencias_ok:
                sys.exit(1)
            if not _validar_resumo_pendencias(args.base_url.rstrip("/")):
                sys.exit(1)
        else:
            print(
                "Proximo passo: rode novamente com `--materializar-pendencias` "
                "para fechar as pendencias materializadas."
            )
    except RuntimeError as error:
        print(f"ERRO: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
