from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

import pandas as pd
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel

UserRole = Literal["admin", "gestor", "analista", "usuario"]

TOKEN_SECRET = os.getenv("ADMSTOIQS_TOKEN_SECRET", "admstoiqs-local-secret")
TOKEN_MAX_AGE_SECONDS = int(os.getenv("ADMSTOIQS_TOKEN_MAX_AGE_SECONDS", str(8 * 60 * 60)))
PASSWORD_ITERATIONS = 120_000
INITIAL_PASSWORD = "inicio123"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SECURITY_DIR = PROJECT_ROOT / "data" / "security"
USERS_PARQUET = SECURITY_DIR / "usuarios.parquet"
USER_AUDIT_PARQUET = PROJECT_ROOT / "data" / "logs" / "log_usuarios.parquet"

serializer = URLSafeTimedSerializer(TOKEN_SECRET, salt="admstoiqs-auth")
security = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    usuario: str
    nome_usuario: str
    perfil: UserRole


LOCAL_USERS: dict[str, dict[str, str]] = {
    "admin": {
        "senha_hash": hashlib.sha256("admin123".encode("utf-8")).hexdigest(),
        "nome_usuario": "Administrador",
        "perfil": "admin",
    },
    "gestor": {
        "senha_hash": hashlib.sha256("gestor123".encode("utf-8")).hexdigest(),
        "nome_usuario": "Gestor",
        "perfil": "gestor",
    },
    "usuario": {
        "senha_hash": hashlib.sha256("usuario123".encode("utf-8")).hexdigest(),
        "nome_usuario": "Analista",
        "perfil": "analista",
    },
}


def authenticate_user(usuario: str, senha: str) -> AuthUser | None:
    normalized = usuario.strip().lower()
    persisted = _get_persisted_user(normalized)
    record = persisted or LOCAL_USERS.get(normalized)
    if record is None:
        return None
    if str(record.get("status", "ativo")).lower() != "ativo":
        return None
    if not _verify_password(senha, str(record["senha_hash"])):
        return None
    return AuthUser(
        usuario=str(record.get("usuario") or normalized),
        nome_usuario=str(record.get("nome_usuario") or normalized),
        perfil=str(record.get("perfil") or "analista"),  # type: ignore[arg-type]
    )


def is_password_change_required(usuario: str) -> bool:
    record = _get_persisted_user(usuario.strip().lower())
    if record is None:
        return False
    return str(record.get("troca_senha_obrigatoria", "false")).lower() == "true"


def change_initial_password(
    *,
    usuario: str,
    senha_atual: str,
    nova_senha: str,
    ip: str = "",
    pc: str = "",
) -> None:
    normalized = usuario.strip().lower()
    if len(nova_senha) < 8:
        raise ValueError("A nova senha deve ter pelo menos 8 caracteres.")
    if nova_senha == INITIAL_PASSWORD:
        raise ValueError("A nova senha deve ser diferente da senha inicial.")

    users = _load_users()
    if users.empty or "usuario" not in users.columns:
        raise ValueError("Usuário não encontrado.")

    mask = users["usuario"].astype(str).str.lower() == normalized
    if not mask.any():
        raise ValueError("Usuário não encontrado.")

    index = users[mask].index[-1]
    stored_hash = str(users.loc[index, "senha_hash"])
    if not _verify_password(senha_atual, stored_hash):
        raise ValueError("Senha atual inválida.")

    now = datetime.now().isoformat(timespec="seconds")
    users.loc[index, "senha_hash"] = _hash_password(nova_senha)
    users.loc[index, "troca_senha_obrigatoria"] = "false"
    users.loc[index, "atualizado_em"] = now
    users.loc[index, "atualizado_por"] = normalized
    _save_users(users)
    _append_user_audit(
        {
            "acao": "alterar_senha_inicial",
            "usuario_alvo": normalized,
            "perfil_alvo": str(users.loc[index, "perfil"]),
            "usuario_responsavel": normalized,
            "ip": ip,
            "pc": pc,
            "registrado_em": now,
        }
    )


def create_access_token(user: AuthUser) -> str:
    payload = {
        "sub": user.usuario,
        "nome_usuario": user.nome_usuario,
        "perfil": user.perfil,
        "exp": int((datetime.now(timezone.utc) + timedelta(seconds=TOKEN_MAX_AGE_SECONDS)).timestamp()),
    }
    return serializer.dumps(payload)


def decode_access_token(token: str) -> AuthUser:
    try:
        payload = serializer.loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except SignatureExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado.",
        ) from exc
    except BadSignature as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        ) from exc

    exp = int(payload.get("exp", 0))
    if exp and exp < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado.",
        )

    return AuthUser(
        usuario=str(payload["sub"]),
        nome_usuario=str(payload["nome_usuario"]),
        perfil=str(payload["perfil"]),  # type: ignore[arg-type]
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> AuthUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação obrigatória.",
        )
    user = decode_access_token(credentials.credentials)
    if is_password_change_required(user.usuario):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Troca de senha obrigatória antes do acesso.",
        )
    return user


def require_roles(*roles: UserRole):
    def dependency(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
        if user.perfil not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Perfil sem permissão para esta operação.",
            )
        return user

    return dependency


def request_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return ""


def list_users() -> list[dict[str, str]]:
    records = _load_users()
    if records.empty:
        fallback = []
        for usuario, record in LOCAL_USERS.items():
            fallback.append(
                {
                    "usuario": usuario,
                    "email": usuario,
                    "nome_usuario": record["nome_usuario"],
                    "perfil": record["perfil"],
                    "status": "ativo",
                    "troca_senha_obrigatoria": "false",
                    "segundo_fator_obrigatorio": "false",
                    "criado_em": "",
                    "criado_por": "dev",
                }
            )
        return fallback

    visible_columns = [
        "usuario",
        "email",
        "nome_usuario",
        "perfil",
        "status",
        "troca_senha_obrigatoria",
        "segundo_fator_obrigatorio",
        "criado_em",
        "criado_por",
    ]
    for column in visible_columns:
        if column not in records.columns:
            records[column] = ""
    return records[visible_columns].fillna("").astype(str).to_dict("records")


def create_user(
    *,
    email: str,
    nome_usuario: str,
    perfil: str,
    criado_por: str,
    ip: str = "",
    pc: str = "",
) -> dict[str, str]:
    normalized_email = email.strip().lower()
    normalized_profile = perfil.strip().lower()
    if "@" not in normalized_email:
        raise ValueError("Informe um e-mail válido para cadastro.")
    if normalized_profile not in {"admin", "gestor", "analista"}:
        raise ValueError("Perfil deve ser admin, gestor ou analista.")

    users = _load_users()
    if not users.empty and "usuario" in users.columns:
        exists = users["usuario"].astype(str).str.lower().eq(normalized_email).any()
        if exists:
            raise ValueError("Usuário já cadastrado.")

    now = datetime.now().isoformat(timespec="seconds")
    record = {
        "usuario": normalized_email,
        "email": normalized_email,
        "nome_usuario": nome_usuario.strip() or normalized_email,
        "perfil": normalized_profile,
        "status": "ativo",
        "senha_hash": _hash_password(INITIAL_PASSWORD),
        "troca_senha_obrigatoria": "true",
        "segundo_fator_obrigatorio": "true",
        "segundo_fator_configurado": "false",
        "criado_em": now,
        "criado_por": criado_por,
        "atualizado_em": now,
        "atualizado_por": criado_por,
    }

    updated = pd.concat([users, pd.DataFrame([record])], ignore_index=True)
    _save_users(updated)
    _append_user_audit(
        {
            "acao": "criar_usuario",
            "usuario_alvo": normalized_email,
            "perfil_alvo": normalized_profile,
            "usuario_responsavel": criado_por,
            "ip": ip,
            "pc": pc,
            "registrado_em": now,
        }
    )

    response = {k: v for k, v in record.items() if k != "senha_hash"}
    response["senha_inicial"] = INITIAL_PASSWORD
    return response


def _load_users() -> pd.DataFrame:
    if not USERS_PARQUET.exists():
        return pd.DataFrame()
    return pd.read_parquet(USERS_PARQUET)


def _save_users(users: pd.DataFrame) -> None:
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    users.to_parquet(USERS_PARQUET, index=False)


def _get_persisted_user(usuario: str) -> dict[str, str] | None:
    users = _load_users()
    if users.empty or "usuario" not in users.columns:
        return None
    match = users[users["usuario"].astype(str).str.lower() == usuario]
    if match.empty:
        return None
    return {key: str(value) for key, value in match.iloc[-1].fillna("").to_dict().items()}


def _hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        _, iterations, salt, digest = stored_hash.split("$", 3)
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(computed, digest)
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored_hash)


def _append_user_audit(record: dict[str, str]) -> None:
    USER_AUDIT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    incoming = pd.DataFrame([record])
    if USER_AUDIT_PARQUET.exists():
        current = pd.read_parquet(USER_AUDIT_PARQUET)
        incoming = pd.concat([current, incoming], ignore_index=True)
    incoming.to_parquet(USER_AUDIT_PARQUET, index=False)


def force_password_reset(
    *,
    usuario: str,
    responsavel: str,
    ip: str = "",
    pc: str = "",
) -> dict[str, str]:
    normalized = usuario.strip().lower()
    users = _load_users()
    if users.empty or "usuario" not in users.columns:
        raise ValueError("Usuário não encontrado.")

    mask = users["usuario"].astype(str).str.lower() == normalized
    if not mask.any():
        raise ValueError("Usuário não encontrado.")

    index = users[mask].index[-1]
    now = datetime.now().isoformat(timespec="seconds")
    users.loc[index, "senha_hash"] = _hash_password(INITIAL_PASSWORD)
    users.loc[index, "troca_senha_obrigatoria"] = "true"
    users.loc[index, "segundo_fator_obrigatorio"] = "true"
    users.loc[index, "atualizado_em"] = now
    users.loc[index, "atualizado_por"] = responsavel
    _save_users(users)
    _append_user_audit(
        {
            "acao": "forcar_reset_senha",
            "usuario_alvo": normalized,
            "perfil_alvo": str(users.loc[index, "perfil"]),
            "usuario_responsavel": responsavel,
            "ip": ip,
            "pc": pc,
            "registrado_em": now,
        }
    )
    return {
        "usuario": normalized,
        "senha_inicial": INITIAL_PASSWORD,
        "troca_senha_obrigatoria": "true",
    }
