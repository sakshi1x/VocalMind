from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
	CategoryCreateRequest,
	CategoryResponse,
	CategoryUpdateRequest,
	MessageResponse,
)
from services.auth_service.app.api_keys import API_KEY_HEADER
from services.auth_service.app.api_keys import verify_api_key, AuthContext
from shared.database.services import category as category_crud
from shared.database.models import Category
from shared.database.session import get_db

router = APIRouter(prefix="/categories", tags=["Categories"])


def _serialize_category(category: Category) -> CategoryResponse:
	return CategoryResponse(
		id=category.id,
		app_id=str(category.app_id),
		categories=category.categories,
	)

@router.post(
	"",
	response_model=CategoryResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Create category",
	responses={401: {"description": "Unauthorized"}},
)
async def create_category(
	body: CategoryCreateRequest,
	auth_ctx: AuthContext = Depends(verify_api_key),
	db: AsyncSession = Depends(get_db),
):
	"""
	Create a new category record.
	"""
	category = await category_crud.create_category(
		db=db,
		app_id=auth_ctx.user_id,
		categories=body.categories,
	)
	return _serialize_category(category)


@router.get(
	"",
	response_model=list[CategoryResponse],
	summary="List categories",
	responses={401: {"description": "Unauthorized"}},
)
async def list_categories(
	auth_ctx: AuthContext = Depends(verify_api_key),
	db: AsyncSession = Depends(get_db),
):
	"""
	Return categories for the authenticated application.
	"""
	categories = await category_crud.get_categories_by_app(db, auth_ctx.user_id)
	return [_serialize_category(category) for category in categories]


@router.get(
	"/{category_id}",
	response_model=CategoryResponse,
	summary="Get category by ID",
	responses={401: {"description": "Unauthorized"}, 404: {"description": "Category not found"}},
)
async def get_category(
	category_id: int,
	_api_key: str | None = Security(API_KEY_HEADER),
	db: AsyncSession = Depends(get_db),
):
	"""
	Return a category record by its identifier.
	"""
	category = await category_crud.get_category(db, category_id)
	if category is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
	return _serialize_category(category)


@router.patch(
	"/{category_id}",
	response_model=CategoryResponse,
	summary="Update category",
	responses={401: {"description": "Unauthorized"}, 404: {"description": "Category not found"}},
)
async def update_category(
	category_id: int,
	body: CategoryUpdateRequest,
	_api_key: str | None = Security(API_KEY_HEADER),
	db: AsyncSession = Depends(get_db),
):
	"""
	Update an existing category record.
	"""
	category = await category_crud.update_category(db, category_id, categories=body.categories)
	if category is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
	return _serialize_category(category)


@router.delete(
	"/{category_id}",
	response_model=MessageResponse,
	summary="Delete category",
	responses={401: {"description": "Unauthorized"}, 404: {"description": "Category not found"}},
)
async def delete_category(
	category_id: int,
	_api_key: str | None = Security(API_KEY_HEADER),
	db: AsyncSession = Depends(get_db),
):
	"""
	Delete a category record by its identifier.
	"""
	deleted = await category_crud.delete_category(db, category_id)
	if not deleted:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
	return MessageResponse(message="Category deleted successfully")
