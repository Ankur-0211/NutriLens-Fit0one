import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AnalysisRecord(Base):
    __tablename__ = "analysis"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("app_user.id"), nullable=True)
    image_id = Column(String(36), ForeignKey("image.id"), nullable=True)
    model_versions = Column(JSON, nullable=False, default=dict)
    nutrition_db_version = Column(String(50), nullable=True)
    visual_labelset_version = Column(String(50), nullable=True)
    identity_map_version = Column(String(50), nullable=True)
    image_quality = Column(JSON, default=dict)
    timings_ms = Column(JSON, default=dict)
    status = Column(String(50), default="completed")
    error_code = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    items = relationship("PredictionItem", back_populates="analysis", cascade="all, delete-orphan")

class PredictionItem(Base):
    __tablename__ = "prediction_item"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analysis.id"), nullable=False)
    item_key = Column(String(50), nullable=False)
    bbox = Column(JSON, nullable=True)  # [ymin, xmin, ymax, xmax] normalized
    mask_ref = Column(String(255), nullable=True)
    coarse_class = Column(String(50), nullable=True)
    detect_conf = Column(Float, nullable=True)
    visual_top_k = Column(JSON, default=list)  # [{"visual_class_id": "...", "p": 0.9}]
    food_id = Column(String(100), ForeignKey("food.id"), nullable=True)
    variant_id = Column(String(120), nullable=True)
    food_conf = Column(Float, nullable=True)
    identity_conf = Column(Float, nullable=True)
    identity_ambiguity = Column(String(50), default="none")  # 'food', 'variant', 'none'
    top_k = Column(JSON, default=list)  # resolved alternative foods
    portion_g = Column(Float, nullable=True)
    portion_lo = Column(Float, nullable=True)
    portion_hi = Column(Float, nullable=True)
    portion_conf = Column(Float, nullable=True)
    portion_method = Column(String(50), nullable=True)
    nutrition = Column(JSON, default=dict)
    nutrition_conf = Column(Float, nullable=True)

    analysis = relationship("AnalysisRecord", back_populates="items")
