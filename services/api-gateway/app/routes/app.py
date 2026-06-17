from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import AppResponse
from services.auth_service.app.api_keys import verify_api_key, AuthContext
from shared.database.services import app as app_crud
from shared.database.models import App
from shared.database.session import get_db

router = APIRouter(prefix="/apps", tags=["Apps"])


def _serialize_app(app: App) -> AppResponse:
    return AppResponse(
        id=str(app.id),
        name=app.name,
        email=app.email,
        is_verified=app.is_verified,
    )


@router.get(
    "",
    response_model=AppResponse,
    summary="Get application details",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Application not found"},
    },
)
async def get_app(
    auth: AuthContext = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Return authenticated application's details.
    """

    app = await app_crud.get_app_by_id(db, auth.user_id)

    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return _serialize_app(app)