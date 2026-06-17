from datetime import datetime
from enum import Enum
from typing import Optional,Any

from pydantic import BaseModel, EmailStr, field_validator


# ── Enums ──────────────────────────────────────────────────────────────────────

class AudioStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class PipelineStage(str, Enum):
    audio_service = "audio_service"
    asr_service = "asr_service"
    language_service = "language_service"
    translation_service = "translation_service"
    nlp_service = "nlp_service"
    urgency_service = "urgency_service"
    persistence_service = "persistence_service"
    completed = "completed"


# ── Auth schemas ───────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CreateApiKeyRequest(BaseModel):
    expires_in_days: Optional[int] = None

    @field_validator("expires_in_days")
    @classmethod
    def validate_expires_in_days(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value

        if value <= 0:
            raise ValueError("expires_in_days must be greater than 0")

        return value

class CreateApiKeyResponse(BaseModel):
    api_key: str
    expires_on: Optional[datetime] = None


class RevokeApiKeyResponse(BaseModel):
    message: str


class MessageResponse(BaseModel):
    message: str


class AppResponse(BaseModel):
    id: str
    name: str
    email: str
    is_verified: bool


class CategoryUpdateRequest(BaseModel):
    categories: Optional[dict | list] = None


class CategoryResponse(BaseModel):
    id: int
    app_id: str
    categories: dict | list


class CategoryCreateRequest(BaseModel):
    categories: list[str] | dict[str, Any]
class AudioResponse(BaseModel):
    id: str
    app_id: str
    url: str
    status: str
    current_stage: str


class AudioUpdateRequest(BaseModel):
    url: Optional[str] = None
    status: Optional[str] = None
    current_stage: Optional[str] = None


class GrievanceResponse(BaseModel):
    id: str
    audio_id: str
    beneficiary_id: str
    confidence: Optional[float] = None
    transcript: str
    language: str
    grievance_detected: bool
    category: Optional[str] = None
    sentiment: Optional[str] = None
    urgency: Optional[str] = None
    severity_score: Optional[float] = None
    recommended_action: Optional[str] = None
    keywords: Optional[list] = None
    created_at: datetime
    updated_at: datetime
    api_key_id: Optional[int] = None


class GrievanceUpdateRequest(BaseModel):
    transcript: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    grievance_detected: Optional[bool] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None
    urgency: Optional[str] = None
    severity_score: Optional[float] = None
    recommended_action: Optional[str] = None
    keywords: Optional[list] = None

# ── Audio schemas ──────────────────────────────────────────────────────────────

class UploadAudioResponse(BaseModel):
    audio_id: str
    status: AudioStatus


class GrievanceData(BaseModel):
    transcript: Optional[str] = None
    language: Optional[str] = None
    sentiment: Optional[str] = None
    category: Optional[str] = None
    urgency: Optional[str] = None
    severity_score: Optional[float] = None


class AudioStatusResponse(BaseModel):
    audio_id: str
    status: AudioStatus
    current_stage: Optional[PipelineStage] = None
    url: Optional[str] = None
    grievance: Optional[GrievanceData] = None


# ── Error schemas ──────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    detail: str
