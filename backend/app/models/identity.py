from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class LabelsetVersion(Base):
    __tablename__ = "labelset_version"

    id = Column(String(50), primary_key=True)  # 'vis-2026.01'
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    visual_classes = relationship("VisualClass", back_populates="labelset")

class VisualClass(Base):
    __tablename__ = "visual_class"

    id = Column(String(100), primary_key=True)  # 'paneer_red_gravy' (visual namespace, NOT food_id)
    labelset_version = Column(String(50), ForeignKey("labelset_version.id"), primary_key=True)
    display_name = Column(String(150), nullable=False)
    coarse_class = Column(String(50), nullable=True)  # 'curry', 'bread', 'rice', 'dal'
    status = Column(String(20), default="active")

    labelset = relationship("LabelsetVersion", back_populates="visual_classes")

class IdentityMapVersion(Base):
    __tablename__ = "identity_map_version"

    id = Column(String(50), primary_key=True)  # 'idmap-2026.01'
    labelset_version = Column(String(50), ForeignKey("labelset_version.id"), nullable=False)
    reviewed_by = Column(String(100), nullable=True)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class VisualClassMapping(Base):
    __tablename__ = "visual_class_mapping"

    identity_map_version = Column(String(50), ForeignKey("identity_map_version.id"), primary_key=True)
    visual_class_id = Column(String(100), primary_key=True)
    labelset_version = Column(String(50), nullable=False)
    food_variant_id = Column(String(120), ForeignKey("food_variant.id"), primary_key=True)
    weight = Column(Numeric(4, 3), nullable=False)  # 0 to 1, sums to 1 per visual class
    is_default = Column(Boolean, default=False)
