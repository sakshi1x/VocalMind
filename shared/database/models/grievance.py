from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from shared.database.base import Base


class Grievance(Base):
    __tablename__ = "grievances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    audio_id = Column(UUID(as_uuid=True), ForeignKey("audios.id"), nullable=False)
    audio = relationship("Audio", back_populates="grievances")

    beneficiary_id = Column(String, nullable=False)

    confidence = Column(Float, nullable=True)

    transcript = Column(String, nullable=False)

    language = Column(String, nullable=False)

    grievance_detected = Column(Boolean, default=False)

    category = Column(String, nullable=True)

    sentiment = Column(String, nullable=True)

    urgency = Column(String, nullable=True)

    severity_score = Column(Float, nullable=True)

    recommended_action = Column(String, nullable=True)

    keywords = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    api_key_id = Column(
        Integer,
        ForeignKey("api_keys.id"),
        nullable=True
    )

    api_key = relationship("APIKey", back_populates="grievances")