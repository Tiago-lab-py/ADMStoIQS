from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


UserRole = Literal["admin", "gestor", "usuario"]

TOKEN_SECRET = os.getenv("ADMSTOIQS_TOKEN_SECRET", "admstoiqs-dev-secret-change-me")
TOKEN_EXPIRE_MINUTES = int(os.getenv("ADMSTOIQS_TOKEN_EXPIRE_MINUTES", "480"))

security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    usuario: str
    nome_usuario: str
    perfil: UserRole


LOCAL_USERS = {
    "admin": {
        "nome_usuario": "Administrador",
        "perfil": "admin",
        "senha_hash": hashlib.sha256("admin123".encode("utf-8")).hexdigest(),
    },
    "gestor": {
        "nome_usuario": "Gestor",
        "perfil": "gestor",
        "senha_hash": hashlib.sha256("gestor123".encode("utf-8")).hexdigest(),
    },
    "usuario": {
        "nome_usuario": "Usuário",
        "perfil": "usuario",
        "senha_hash": hashlib.sha256("usuario123".encode("utf-8")).hexdigest(),
    },
}


def authenticate_user(usuario: str, senha: str) -> AuthUser | None:
    record = LOCAL_USERS.get(usuario.strip().lower())
    if record is None:
        return None

    senha_hash = hashlib.sha256(senha.encode("utf-8")).hexdigest()
    if not secrets.compare_digest(senha_hash, str(record["senha_hash"])):
        return None

    return AuthUser(
        usuario=usuario.strip().lower(),
        nome_usuario=str(record["nome_usuario"]),
        perfil=record["perfil"],  # type: ignore[arg-type]
    )


def create_access_token(user: AuthUser) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user.usuario,
        "nome_usuario": user.nome_usuario,
        "perfil": user.perfil,
        "exp": int(expires_at.timestamp()),
    }
    payload_encoded = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(payload_encoded)
    return f"{payload_encoded}.{signature}"


def decode_access_token(token: str) -> AuthUser:
    try:
        payload_encoded, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.") from exc

    expected_signature = _sign(payload_encoded)
    if not secrets.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    try:
        payload = json.loads(_base64url_decode(payload_encoded))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.") from exc

    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado.")

    return AuthUser(
        usuario=str(payload["sub"]),
        nome_usuario=str(payload["nome_usuario"]),
        perfil=str(payload["perfil"]),  # type: ignore[arg-type]
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação obrigatória.")

    return decode_access_token(credentials.credentials)


def require_roles(*roles: UserRole):
    def dependency(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.perfil not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perfil sem permissão.")
        return user

    return dependency


def request_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "desconhecido"


def _sign(payload_encoded: str) -> str:
    digest = hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        payload_encoded.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _base64url_encode(digest)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)

