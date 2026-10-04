import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AppUser(Base):
    __tablename__ = "app_user"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    auth_provider = Column(String(50), nullable=False, default="email")
    display_name = Column(String(100), nullable=True)
    age_range = Column(String(20), nullable=True)
    sex = Column(String(20), nullable=True)
    height_cm = Column(Numeric(5, 1), nullable=True)
    weight_kg = Column(Numeric(5, 1), nullable=True)
    timezone = Column(String(50), default="Asia/Kolkata")
    training_consent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    meals = relationship("Meal", back_populates="user", cascade="all, delete-orphan")
