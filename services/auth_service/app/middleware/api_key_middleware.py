import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from shared.database.session import SessionLocal
from services.auth_service.app.api_keys import verify_api_key

logger = logging.getLogger(__name__)

# Paths that don't require API key authentication.
EXCLUDED_PATHS = [
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/register",
    "/auth/login",
]

JWT_AUTH_PATHS = {
    ("GET", "/auth/api-key"),
    ("POST", "/auth/api-key"),
    ("DELETE", "/auth/api-key"),
}


async def api_key_middleware(request: Request, call_next):
    allows_bearer_auth = (request.method, request.url.path) in JWT_AUTH_PATHS

    if any(request.url.path.startswith(path) for path in EXCLUDED_PATHS):
        return await call_next(request)

    if request.headers.get("authorization") and allows_bearer_auth:
        return await call_next(request)

    api_key = request.headers.get("x-api-key")

    if not api_key:
        return JSONResponse(
            status_code=401,
            content={
                "detail": (
                    "API key or Authorization header is required"
                    if allows_bearer_auth
                    else "API key is required"
                )
            },
        )

    db = SessionLocal()
    try:
        auth_context = await verify_api_key(api_key=api_key, db=db)
        request.state.api_key_identifier = auth_context.identifier
        request.state.auth_context = auth_context
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    except Exception:
        await db.rollback()
        logger.exception("Unexpected API key verification failure")
        raise
    finally:
        await db.close()

    return await call_next(request)
