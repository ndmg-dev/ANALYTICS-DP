import hashlib
import os
from fastapi import Header, HTTPException

# Quick shared-password gate for the internal UI — not a full user/session
# system. The token is a deterministic hash of the configured password, so
# no server-side session storage is needed and it survives restarts/replicas.
ACCESS_PASSWORD = os.getenv("APP_ACCESS_PASSWORD", "dpadmin1020")
_SALT = "dp-analytics-access"


def _expected_token() -> str:
    return hashlib.sha256(f"{ACCESS_PASSWORD}{_SALT}".encode()).hexdigest()


def issue_token(password: str) -> str:
    if password != ACCESS_PASSWORD:
        raise HTTPException(status_code=401, detail="Senha incorreta.")
    return _expected_token()


async def require_access(x_access_token: str = Header(default="")):
    if x_access_token != _expected_token():
        raise HTTPException(status_code=401, detail="Acesso não autorizado.")
