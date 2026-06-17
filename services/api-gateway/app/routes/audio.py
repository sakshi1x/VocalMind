import json
from uuid import uuid4

import aio_pika
from fastapi import APIRouter, Depends, File, HTTPException, Request, Security, UploadFile, status
from fastapi import Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import RABBIT_URL, EXCHANGE_NAME, ENTRY_ROUTING_KEY, R2_BUCKET
from app.schemas import (
    AudioResponse,
    AudioUpdateRequest,
    AudioStatus,
    PipelineStage,
    UploadAudioResponse,
    AudioStatusResponse,
    GrievanceData,
    MessageResponse,
    CategoryResponse
)
from shared.database.models import Category
from shared.database.services import category as category_crud
from shared.database.session import get_db        
from shared.database.models.audio import Audio
from services.auth_service.app.api_keys import API_KEY_HEADER
from shared.database.services import audio as audio_crud
from shared.utils.logger import get_queue_logger
from app.utils.s3_handler import upload_file_to_r2

queue_logger = get_queue_logger()
router = APIRouter(prefix="/audio", tags=["Audio"])

def _serialize_category(category: Category) -> CategoryResponse:
	return CategoryResponse(
		id=category.id,
		app_id=str(category.app_id),
		categories=category.categories,
	)
async def _publish_audio_event(payload: dict) -> None:
    queue_logger.info(
        "Opening RabbitMQ connection",
        extra={
            "service": "api-gateway",
            "exchange": EXCHANGE_NAME,
            "routing_key": ENTRY_ROUTING_KEY,
            "event": "publish.start",
        },
    )
    connection = await aio_pika.connect_robust(RABBIT_URL)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    queue_logger.info(
        "Exchange ready for publish",
        extra={
            "service": "api-gateway",
            "exchange": EXCHANGE_NAME,
            "routing_key": ENTRY_ROUTING_KEY,
            "event": "exchange.declared",
        },
    )

    try:
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=ENTRY_ROUTING_KEY,
        )
        queue_logger.info(
            "Exchange publish success",
            extra={
                "service": "api-gateway",
                "exchange": EXCHANGE_NAME,
                "routing_key": ENTRY_ROUTING_KEY,
                "event": "publish.success",
                "request_id": payload.get("request_id"),
            },
        )
    finally:
        await connection.close()



@router.post(
    "",
    response_model=UploadAudioResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload an audio file for grievance processing",
    responses={401: {"description": "Unauthorized"}},
)
async def upload_audio(
    request: Request,
    file: UploadFile = File(..., description="Audio file to process"),
    _api_key: str | None = Security(API_KEY_HEADER),
    category_id: int = Header(..., description="Category ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload an audio file and enqueue it for grievance processing.
    """
    auth_context = getattr(request.state, "auth_context", None)
    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to resolve API key authentication context",
        )


    audio_bytes = await file.read()
    audio_id = str(uuid4())
    filename = file.filename or f"{audio_id}.wav"
    # Upload to R2 
    file_path = upload_file_to_r2(audio_bytes, filename, R2_BUCKET)

    # Persist the audio record immediately, then enqueue
    await audio_crud.create_audio(
        db=db,
        audio_id=audio_id,
        app_id=auth_context.user_id,
        url=file_path,
        status=AudioStatus.uploaded.value,
        current_stage=PipelineStage.audio_service.value,
    )
    category = await category_crud.get_category(db, category_id)
    if  _serialize_category(category).model_dump() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )


    payload = {
        "request_id": audio_id,
        "audio_filename": file_path,
        "filename": filename,
        "app_id": auth_context.user_id,
        "beneficiary_id": auth_context.identifier,
        "api_key_id": auth_context.api_key_id,
        "category":  category.categories,
    }

    queue_logger.info(
        "Publishing audio upload event",
        extra={
            "service": "api-gateway",
            "source": "upload_audio",
            "queue_request_id": audio_id,
            "queue_audio_filename": payload["audio_filename"],
            "exchange": EXCHANGE_NAME,
            "queue_routing_key": ENTRY_ROUTING_KEY,
            "event": "publish.attempt",
        },
    )

    try:
        await _publish_audio_event(payload)
    except Exception as exc:
        await audio_crud.update_audio(
            db=db,
            audio_id=audio_id,
            status=AudioStatus.failed.value,
            current_stage=PipelineStage.audio_service.value,
        )
        queue_logger.error(
            "Failed to publish audio event",
            exc_info=True,
            extra={
                "service": "api-gateway",
                "source": "upload_audio",
                "queue_request_id": audio_id,
                "queue_audio_filename": payload["audio_filename"],
                "exchange": EXCHANGE_NAME,
                "queue_routing_key": ENTRY_ROUTING_KEY,
                "event": "publish.failure",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish audio: {exc}",
        ) from exc

    queue_logger.info(
        "Published audio upload event",
        extra={
            "service": "api-gateway",
            "source": "upload_audio",
            "queue_request_id": audio_id,
            "queue_audio_filename": payload["audio_filename"],
            "exchange": EXCHANGE_NAME,
            "queue_routing_key": ENTRY_ROUTING_KEY,
            "event": "publish.success",
        },
    )

    return UploadAudioResponse(
        audio_id=audio_id,
        status=AudioStatus.uploaded,
    )



@router.get(
    "/{audio_id}",
    response_model=AudioStatusResponse,
    summary="Get audio processing status and results",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Audio not found"},
        500: {"description": "Processing error"},
    },
)
async def get_audio_status(
    audio_id: str,
    _api_key: str | None = Security(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the processing status and latest grievance result for a specific audio record.
    """
    queue_logger.info(
        "Audio status requested",
        extra={
            "service": "api-gateway",
            "source": "get_audio_status",
            "audio_id": audio_id,
            "event": "status.query",
        },
    )

    # TODO: query persistence-service for the audio record
    result = await db.execute(
        select(Audio)
        .where(Audio.id == audio_id)
        .options(selectinload(Audio.grievances))
    )
    audio = result.scalar_one_or_none()

    if audio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

    grievance = audio.grievances[-1] if audio.grievances else None

    return AudioStatusResponse(
        audio_id=str(audio.id),
        status=AudioStatus(audio.status),
        current_stage=PipelineStage(audio.current_stage),
        url=audio.url,
        grievance=GrievanceData(
            transcript=grievance.transcript if grievance else None,
            language=grievance.language if grievance else None,
            sentiment=grievance.sentiment if grievance else None,
            category=grievance.category if grievance else None,
            urgency=grievance.urgency if grievance else None,
            severity_score=grievance.severity_score if grievance else None,
        ) if grievance else None,
    )


def _serialize_audio(audio: Audio) -> AudioResponse:
    return AudioResponse(
        id=str(audio.id),
        app_id=str(audio.app_id),
        url=audio.url,
        status=audio.status,
        current_stage=audio.current_stage,
    )



from services.auth_service.app.api_keys import verify_api_key, AuthContext

@router.get(
    "",
    response_model=list[AudioResponse],
    summary="List audio records",
    responses={401: {"description": "Unauthorized"}},
)
async def list_audio(
    auth_ctx: AuthContext = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Return audio records for the authenticated application.
    """
    audios = await audio_crud.get_audios_by_app(db, auth_ctx.user_id)
    return [_serialize_audio(audio) for audio in audios]


@router.patch(
    "/{audio_id}",
    response_model=AudioResponse,
    summary="Update audio record",
    responses={401: {"description": "Unauthorized"}, 404: {"description": "Audio not found"}},
)
async def update_audio(
    audio_id: str,
    body: AudioUpdateRequest,
    _api_key: str | None = Security(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing audio record.
    """
    audio = await audio_crud.update_audio(
        db,
        audio_id,
        url=body.url,
        status=body.status,
        current_stage=body.current_stage,
    )
    if audio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")
    return _serialize_audio(audio)


@router.delete(
    "/{audio_id}",
    response_model=MessageResponse,
    summary="Delete audio record",
    responses={401: {"description": "Unauthorized"}, 404: {"description": "Audio not found"}},
)
async def delete_audio(
    audio_id: str,
    _api_key: str | None = Security(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an audio record by its identifier.
    """
    deleted = await audio_crud.delete_audio(db, audio_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")
    return MessageResponse(message="Audio deleted successfully")