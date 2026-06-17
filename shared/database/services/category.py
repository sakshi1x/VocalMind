from typing import Optional
 
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
 
from shared.database.models import Category



async def create_category(
    db: AsyncSession,
    app_id,
    categories: dict | list,
) -> Category:
    category = Category(
        app_id=app_id,
        categories=categories,
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return category

 
async def get_category(db: AsyncSession, category_id: int) -> Optional[Category]:
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()
 
 
async def get_categories_by_app(
    db: AsyncSession, app_id: str, skip: int = 0, limit: int = 100
) -> list[Category]:
    result = await db.execute(
        select(Category).where(Category.app_id == app_id).offset(skip).limit(limit)
    )
    return result.scalars().all()
 
 
async def get_all_categories(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Category]:
    result = await db.execute(select(Category).offset(skip).limit(limit))
    return result.scalars().all()
 
 
async def update_category(
    db: AsyncSession,
    category_id: int,
    categories: Optional[dict | list] = None,
) -> Optional[Category]:
    category = await get_category(db, category_id)
    if not category:
        return None
 
    if categories is not None:
        category.categories = categories
 
    await db.commit()
    await db.refresh(category)
    return category
 
 
async def delete_category(db: AsyncSession, category_id: int) -> bool:
    category = await get_category(db, category_id)
    if not category:
        return False
    await db.delete(category)
    await db.commit()
    return True