from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT_DIR / ".env"


def _load_dotenv_if_needed() -> None:
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class IqsSettings:
    uid: str
    pwd: str
    db: str
    config_dir: str

    @property
    def configured(self) -> bool:
        return bool(self.uid and self.pwd and self.db and self.config_dir)

    def masked(self) -> dict[str, str | bool]:
        return {
            "IQS_UID": self.uid,
            "IQS_PWD": "***" if self.pwd else "",
            "IQS_DB": self.db,
            "IQS_CONFIG_DIR": self.config_dir,
            "configured": self.configured,
        }


def get_iqs_settings() -> IqsSettings:
    _load_dotenv_if_needed()
    return IqsSettings(
        uid=os.getenv("IQS_UID", "").strip(),
        pwd=os.getenv("IQS_PWD", "").strip(),
        db=os.getenv("IQS_DB", "").strip(),
        config_dir=os.getenv("IQS_CONFIG_DIR", "").strip(),
    )

