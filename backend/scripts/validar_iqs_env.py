from __future__ import annotations

from pathlib import Path

from backend.app.core.iqs_settings import get_iqs_settings


def main() -> None:
    settings = get_iqs_settings()
    masked = settings.masked()
    config_dir = Path(settings.config_dir) if settings.config_dir else None
    tnsnames_path = config_dir / "tnsnames.ora" if config_dir else None

    print("Configuração IQS:")
    print(f"IQS_UID: {masked['IQS_UID']}")
    print(f"IQS_PWD: {masked['IQS_PWD']}")
    print(f"IQS_DB: {masked['IQS_DB']}")
    print(f"IQS_CONFIG_DIR: {masked['IQS_CONFIG_DIR']}")
    print(f"Diretório existe: {config_dir.exists() if config_dir else False}")
    print(f"tnsnames.ora existe: {tnsnames_path.exists() if tnsnames_path else False}")
    print(f"Configurado: {masked['configured']}")

    if not settings.configured:
        print("Atenção: preencha IQS_PWD e IQS_CONFIG_DIR no arquivo .env local antes de executar extrações IQS.")
        return

    if not config_dir or not config_dir.exists():
        print("Atenção: IQS_CONFIG_DIR não foi encontrado no filesystem.")
        return

    if not tnsnames_path or not tnsnames_path.exists():
        print("Atenção: tnsnames.ora não foi encontrado em IQS_CONFIG_DIR.")
        return

    print("Configuração IQS local validada. Próximo passo: testar conexão Oracle.")


if __name__ == "__main__":
    main()

