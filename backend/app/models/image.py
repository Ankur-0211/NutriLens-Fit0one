import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class ImageRecord(Base):
    __tablename__ = "image"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("app_user.id"), nullable=True)
    storage_key = Column(String(255), nullable=False)
    sha256 = Column(String(64), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    bytes = Column(Integer, nullable=True)
    retention_class = Column(String(50), nullable=False, default="transient")  # transient, meal_linked, training_consented
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
