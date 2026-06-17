from typing import Optional
import uuid
 
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
 
from shared.database.models import Audio

 
async def get_audio(
    db: AsyncSession,
    audio_id: str,
    load_grievances: bool = False,
) -> Optional[Audio]:
    query = select(Audio).where(Audio.id == audio_id)
    if load_grievances:
        query = query.options(selectinload(Audio.grievances))
    result = await db.execute(query)
    return result.scalar_one_or_none()
 
 
async def get_audios_by_app(
    db: AsyncSession,
    app_id: str,
    skip: int = 0,
    limit: int = 100,
) -> list[Audio]:
    result = await db.execute(
        select(Audio).where(Audio.app_id == app_id).offset(skip).limit(limit)
    )
    return result.scalars().all()
 
 
async def get_all_audios(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> list[Audio]:
    result = await db.execute(select(Audio).offset(skip).limit(limit))
    return result.scalars().all()
 
 
async def create_audio(
    db: AsyncSession,
    audio_id: str,
    app_id: str,
    url: str,
    status: str,
    current_stage: str,
) -> Audio:
    audio = Audio(
        id=uuid.UUID(audio_id),
        app_id=app_id,
        url=url,
        status=status,
        current_stage=current_stage,
    )
    db.add(audio)
    await db.commit()
    await db.refresh(audio)
    return audio
 
 
async def update_audio(
    db: AsyncSession,
    audio_id: str,
    url: Optional[str] = None,
    status: Optional[str] = None,
    current_stage: Optional[str] = None,
) -> Optional[Audio]:
    audio = await get_audio(db, audio_id)
    if not audio:
        return None
 
    if url is not None:
        audio.url = url
    if status is not None:
        audio.status = status
    if current_stage is not None:
        audio.current_stage = current_stage
 
    await db.commit()
    await db.refresh(audio)
    return audio
 
 
async def delete_audio(db: AsyncSession, audio_id: str) -> bool:
    audio = await get_audio(db, audio_id)
    if not audio:
        return False
    await db.delete(audio)
    await db.commit()
    return True