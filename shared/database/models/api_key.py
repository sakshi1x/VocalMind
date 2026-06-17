from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from datetime import datetime

from shared.database.base import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)

    identifier = Column(String, nullable=False)

    api_key_hash = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)

    expires_on = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    
    last_used_at = Column(DateTime, nullable=True)

    app_id = Column(String, nullable=True)

    scopes = Column(String, nullable=True)

    rate_limit = Column(Integer, nullable=True)

    grievances = relationship("Grievance", back_populates="api_key")