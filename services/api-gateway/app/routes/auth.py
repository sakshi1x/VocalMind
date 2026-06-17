import uuid
from datetime import datetime, timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    CreateApiKeyRequest,
    RevokeApiKeyResponse,
    CreateApiKeyResponse,
)
from cryptography.fernet import InvalidToken
from services.auth_service.app.password_security import hash_password, verify_password
from shared.database.models import APIKey, App
from shared.database.session import get_db
from services.auth_service.app.api_keys import decrypt_api_key, encrypt_api_key
from services.auth_service.app.jwt import create_access_token, decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Auth"])


async def get_authenticated_app(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
) -> App:
    token = credentials.credentials

    try:
        claims = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    email = claims.get("email")
    subject = claims.get("sub")
    if not email or not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is missing required claims")

    result = await db.execute(
        select(App).where(App.email == email, App.is_verified.is_(True))
    )
    app = result.scalar_one_or_none()
    if app is None or str(app.id) != str(subject):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token for application")

    return app


async def get_active_api_key_for_app(app_id: str, db: AsyncSession) -> APIKey | None:
    existing_key_result = await db.execute(
        select(APIKey).where(
            APIKey.app_id == str(app_id),
            APIKey.is_active.is_(True),
        )
    )
    return existing_key_result.scalar_one_or_none()

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new application",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new application with a name and email.
    """
    existing_app = await db.execute(select(App).where(App.email == body.email))
    if existing_app.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application with this email already exists",
        )

    app = App(
        id=uuid.uuid4(),
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        is_verified=True,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)

    return RegisterResponse(message="Email registered successfully. You can now log in to receive an access token.")


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and receive a JWT token",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with a registered email and receive a JWT access token.
    """

    result = await db.execute(
        select(App).where(
            App.email == body.email,
            App.is_verified.is_(True),
        )
    )

    app = result.scalar_one_or_none()

    if app is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, app.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        subject=str(app.id),
        claims={
            "email": app.email,
            "app_name": app.name,
        },
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/api-key",
    response_model=CreateApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new API key",
    responses={401: {"description": "Unauthorized"}},
)
async def create_api_key(
    body: CreateApiKeyRequest | None = None,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new API key for the authenticated application. Requires a valid JWT access token.
    """    
    app = await get_authenticated_app(credentials=credentials, db=db)

    # Check if an active API key already exists for this app
    existing_key = await get_active_api_key_for_app(app_id=str(app.id), db=db)

    if existing_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active API key already exists for this application. Revoke it before generating a new one.",
        )

    raw_api_key = f"sk_live_{token_urlsafe(24)}"
    expires_on = None
    if body and body.expires_in_days is not None:
        expires_on = datetime.utcnow() + timedelta(days=body.expires_in_days)

    api_key = APIKey(
        identifier=app.name,
        api_key_hash=encrypt_api_key(raw_api_key),
        is_active=True,
        expires_on=expires_on,
        created_at=datetime.utcnow(),
        last_used_at=None,
        app_id=str(app.id),
        scopes=None,
        rate_limit=None,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return CreateApiKeyResponse(
        api_key=raw_api_key,
        expires_on=api_key.expires_on,
    )


@router.get(
    "/api-key",
    response_model=CreateApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the active API key",
    responses={401: {"description": "Unauthorized"}, 404: {"description": "No active key found"}},
)
async def get_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    app = await get_authenticated_app(credentials=credentials, db=db)
    existing_key = await get_active_api_key_for_app(app_id=str(app.id), db=db)

    if not existing_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active API key found")

    try:
        raw_api_key = decrypt_api_key(existing_key.api_key_hash)
    except InvalidToken as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stored API key cannot be decrypted. Revoke it and generate a new one.",
        ) from exc

    return CreateApiKeyResponse(
        api_key=raw_api_key,
        expires_on=existing_key.expires_on,
    )


@router.delete(
    "/api-key",
    response_model=RevokeApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke the active API key",
    responses={401: {"description": "Unauthorized"}, 404: {"description": "No active key found"}},
)
async def revoke_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke the active API key for the authenticated application. Requires a valid JWT access token.
    """
    app = await get_authenticated_app(credentials=credentials, db=db)
    existing_key = await get_active_api_key_for_app(app_id=str(app.id), db=db)
    if not existing_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active API key found")

    existing_key.is_active = False
    await db.commit()
    await db.refresh(existing_key)

    return RevokeApiKeyResponse(message="API key revoked successfully")

