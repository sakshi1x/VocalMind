
import json
from typing import Optional

from shared.database.session import SessionLocal
from shared.database.services import grievance as grievance_crud


async def save_to_db(data: dict) -> Optional[dict]:
    """
    Persist the processed grievance data to the database.
    Expected payload keys:
    - request_id: audio_id
    - transcript: transcribed text
    - language: detected language  
    - app_id: application identifier (used as beneficiary for now)
    - category: grievance category
    - sentiment: sentiment analysis result
    - emotion: emotion analysis result
    - urgency: derived urgency level
    - api_key_id: API key used (for audit)
    """
    print("💾 SAVING TO DB:", json.dumps(data, indent=2))

    try:
        async with SessionLocal() as db:
            # Extract fields from message payload
            audio_id = data.get("request_id")
            beneficiary_id = data.get("beneficiary_id") or data.get("app_id")
            transcript = data.get("transcript", "")
            language = data.get("language", "en")
            category = data.get("category")
            sentiment = data.get("sentiment")
            emotion = data.get("emotion")
            urgency = data.get("urgency")
            api_key_id = data.get("api_key_id")
            
            # NLP confidence and keywords
            confidence = data.get("category_confidence")
            keywords = None
            if emotion:
                keywords = [emotion]
            
            # Derive grievance_detected based on category
            grievance_detected = category and category != "general_feedback"
            
            # Create the grievance record
            grievance = await grievance_crud.create_grievance(
                db=db,
                audio_id=audio_id,
                beneficiary_id=beneficiary_id,
                transcript=transcript,
                language=language,
                api_key_id=api_key_id,
                confidence=confidence,
                grievance_detected=grievance_detected,
                category=category,
                sentiment=sentiment,
                urgency=urgency,
                severity_score=None,
                recommended_action=None,
                keywords=keywords,
            )

            # Update audio record to completion
            from shared.database.services import audio as audio_crud
            await audio_crud.update_audio(
                db=db,
                audio_id=audio_id,
                status="completed",
                current_stage="persistence_service",
            )

            return {
                "grievance_id": str(grievance.id),
                "audio_id": audio_id,
                "status": "persisted",
            }

    except Exception as e:
        print(f"❌ Error persisting to database: {e}")
        raise

