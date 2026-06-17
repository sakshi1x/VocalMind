from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from shared.database.base import Base


class Audio(Base):
    __tablename__ = "audios"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=False)
    app = relationship("App", backref="audios")
    grievances = relationship("Grievance", back_populates="audio")
    url = Column(String, nullable=False)
    status = Column(String, nullable=False)
    current_stage = Column(String, nullable=False)
