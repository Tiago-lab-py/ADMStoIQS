from __future__ import annotations

import os
import time

from backend.app.core.iqs_settings import get_iqs_settings


def _connect_with_oracledb(settings):
    import oracledb

    os.environ["TNS_ADMIN"] = settings.config_dir
    return oracledb.connect(
        user=settings.uid,
        password=settings.pwd,
        dsn=settings.db,
        config_dir=settings.config_dir,
    )


def _connect_with_cx_oracle(settings):
    import cx_Oracle

    os.environ["TNS_ADMIN"] = settings.config_dir
    return cx_Oracle.connect(
        user=settings.uid,
        password=settings.pwd,
        dsn=settings.db,
    )


def main() -> None:
    settings = get_iqs_settings()

    print("Teste de conexão IQS Oracle")
    print(f"Usuário: {settings.uid}")
    print("Senha: ***")
    print(f"DSN: {settings.db}")
    print(f"TNS_ADMIN: {settings.config_dir}")

    if not settings.configured:
        raise SystemExit("Configuração incompleta. Rode primeiro: python -m backend.scripts.validar_iqs_env")

    attempts = [
        ("oracledb", _connect_with_oracledb),
        ("cx_Oracle", _connect_with_cx_oracle),
    ]

    errors: list[str] = []
    started = time.perf_counter()

    for driver_name, connect_func in attempts:
        try:
            print(f"Tentando driver: {driver_name}")
            with connect_func(settings) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM DUAL")
                    value = cursor.fetchone()[0]
            elapsed = time.perf_counter() - started
            print(f"Conexão IQS OK usando {driver_name}. SELECT 1 retornou: {value}")
            print(f"Duração: {elapsed:.2f}s")
            return
        except ModuleNotFoundError as exc:
            errors.append(f"{driver_name}: módulo não instalado ({exc.name})")
        except Exception as exc:
            errors.append(f"{driver_name}: {type(exc).__name__}: {exc}")

    print("Não foi possível conectar ao IQS.")
    print("Tentativas:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()

