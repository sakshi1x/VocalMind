from typing import Optional
import uuid
 
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
 
from shared.database.models import Grievance

 
async def get_grievance(db: AsyncSession, grievance_id: str) -> Optional[Grievance]:
    result = await db.execute(select(Grievance).where(Grievance.id == grievance_id))
    return result.scalar_one_or_none()
 
 
async def create_grievance(
    db: AsyncSession,
    audio_id: str,
    beneficiary_id: str,
    transcript: str,
    language: str,
    api_key_id: int | None = None,
    confidence: float | None = None,
    grievance_detected: bool | None = None,
    category: str | None = None,
    sentiment: str | None = None,
    urgency: str | None = None,
    severity_score: float | None = None,
    recommended_action: str | None = None,
    keywords: list | None = None,
) -> Grievance:
    grievance = Grievance(
        id=uuid.uuid4(),
        audio_id=uuid.UUID(audio_id),
        beneficiary_id=beneficiary_id,
        transcript=transcript,
        language=language,
        api_key_id=api_key_id,
        confidence=confidence,
        grievance_detected=grievance_detected if grievance_detected is not None else False,
        category=category,
        sentiment=sentiment,
        urgency=urgency,
        severity_score=severity_score,
        recommended_action=recommended_action,
        keywords=keywords,
    )
    db.add(grievance)
    await db.commit()
    await db.refresh(grievance)
    return grievance
 
 
async def get_grievances_by_audio(
    db: AsyncSession, audio_id: str, skip: int = 0, limit: int = 100
) -> list[Grievance]:
    result = await db.execute(
        select(Grievance).where(Grievance.audio_id == audio_id).offset(skip).limit(limit)
    )
    return result.scalars().all()
 
 
async def get_all_grievances(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Grievance]:
    result = await db.execute(select(Grievance).offset(skip).limit(limit))
    return result.scalars().all()
 
 
async def update_grievance(
    db: AsyncSession,
    grievance_id: str,
    transcript: Optional[str] = None,
    language: Optional[str] = None,
    confidence: Optional[float] = None,
    grievance_detected: Optional[bool] = None,
    category: Optional[str] = None,
    sentiment: Optional[str] = None,
    urgency: Optional[str] = None,
    severity_score: Optional[float] = None,
    recommended_action: Optional[str] = None,
    keywords: Optional[list] = None,
) -> Optional[Grievance]:
    grievance = await get_grievance(db, grievance_id)
    if not grievance:
        return None
 
    if transcript is not None:
        grievance.transcript = transcript
    if language is not None:
        grievance.language = language
    if confidence is not None:
        grievance.confidence = confidence
    if grievance_detected is not None:
        grievance.grievance_detected = grievance_detected
    if category is not None:
        grievance.category = category
    if sentiment is not None:
        grievance.sentiment = sentiment
    if urgency is not None:
        grievance.urgency = urgency
    if severity_score is not None:
        grievance.severity_score = severity_score
    if recommended_action is not None:
        grievance.recommended_action = recommended_action
    if keywords is not None:
        grievance.keywords = keywords
 
    await db.commit()
    await db.refresh(grievance)
    return grievance
 
 
async def delete_grievance(db: AsyncSession, grievance_id: str) -> bool:
    grievance = await get_grievance(db, grievance_id)
    if not grievance:
        return False
    await db.delete(grievance)
    await db.commit()
    return True
 