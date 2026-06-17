from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import App


async def get_app_by_id(
    db: AsyncSession,
    app_id: str,
) -> App | None:
    result = await db.execute(
        select(App).where(App.id == app_id)
    )

    return result.scalar_one_or_none()