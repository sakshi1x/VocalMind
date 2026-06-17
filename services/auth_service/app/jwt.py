from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError

from services.auth_service.config import settings


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
	now = datetime.now(timezone.utc)
	payload: dict[str, Any] = {
		"sub": subject,
		"iat": now,
		"exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
		"iss": settings.JWT_ISSUER,
		"aud": settings.JWT_AUDIENCE,
	}
	if claims:
		payload.update(claims)

	return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
	try:
		return jwt.decode(
			token,
			settings.JWT_SECRET_KEY,
			algorithms=[settings.JWT_ALGORITHM],
			audience=settings.JWT_AUDIENCE,
			issuer=settings.JWT_ISSUER,
		)
	except InvalidTokenError as exc:
		raise ValueError("Invalid access token") from exc
