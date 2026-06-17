import base64
import json
import logging
from datetime import datetime
from functools import lru_cache
from typing import List, Optional

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.config import settings
from shared.database.models import APIKey
from shared.database.session import get_db

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

class AuthContext:
    def __init__(self, user_id: Optional[str], tenant_id: Optional[str], scopes: Optional[List[str]], api_key_id: int, identifier: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.scopes = scopes or []
        self.api_key_id = api_key_id
        self.identifier = identifier

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "scopes": self.scopes,
            "api_key_id": self.api_key_id,
            "identifier": self.identifier,
        }



@lru_cache(maxsize=1)
def get_api_key_cipher() -> Fernet:
    secret = settings.API_KEY_ENCRYPTION_SECRET
    if not secret:
        raise RuntimeError("API_KEY_ENCRYPTION_SECRET must be set")

    try:
        secret_bytes = secret.encode("utf-8")
        normalized_key = base64.urlsafe_b64encode(secret_bytes[:32].ljust(32, b"0"))
        return Fernet(normalized_key)
    except (ValueError, TypeError, base64.binascii.Error) as exc:
        raise RuntimeError(
            "API_KEY_ENCRYPTION_SECRET could not be converted into an encryption key"
        ) from exc


def encrypt_api_key(raw_key: str) -> str:
    return get_api_key_cipher().encrypt(raw_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    return get_api_key_cipher().decrypt(encrypted_key.encode("utf-8")).decode("utf-8")


def utcnow_naive() -> datetime:
    return datetime.utcnow()


async def get_api_key_record(api_key: str, db: AsyncSession) -> Optional[APIKey]:
    result = await db.execute(select(APIKey).where(APIKey.is_active.is_(True)))
    for record in result.scalars():
        try:
            if decrypt_api_key(record.api_key_hash) == api_key:
                return record
        except InvalidToken:
            continue

    return None


async def verify_api_key(
    api_key: str = Security(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """FastAPI dependency that validates the X-API-Key header."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    record = await get_api_key_record(api_key=api_key, db=db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )
    if record.expires_on and record.expires_on < utcnow_naive():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )
    record.last_used_at = utcnow_naive()
    await db.commit()
    logger.info(f"Authenticated: {record.identifier}")
    # Parse scopes (assume comma-separated or JSON string)
    scopes = []
    if record.scopes:
        try:
            scopes = json.loads(record.scopes)
            if not isinstance(scopes, list):
                scopes = []
        except Exception:
            scopes = [s.strip() for s in record.scopes.split(",") if s.strip()]
    return AuthContext(
        user_id=record.app_id,
        tenant_id=None,
        scopes=scopes,
        api_key_id=record.id,
        identifier=record.identifier,
    )
