import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class ModelVersion(Base):
    """
    ML Model Version Registry (SDD Section 22 lines 1454-1457, Section 25.1).
    Tracks detector, classifier, and portion estimation models across lifecycle stages:
    'staging' -> 'shadow' -> 'canary' -> 'production' -> 'archived'.
    """
    __tablename__ = "model_version"

    id = Column(String(50), primary_key=True)  # e.g., 'cls-0.5.0', 'det-0.3.1', 'por-0.2.0'
    kind = Column(String(50), nullable=False)   # 'classifier', 'detector', 'portion', 'identity_resolver'
    mlflow_run_id = Column(String(100), nullable=True)
    labelset_version = Column(String(50), nullable=True)  # e.g., 'vis-2026.01'
    dataset_version = Column(String(50), nullable=True)   # e.g., 'ds-2026.01'
    metrics = Column(JSON, default=dict)                 # e.g. {"top1": 0.88, "top3": 0.96, "ece": 0.08}
    stage = Column(String(50), default="staging", nullable=False)  # 'staging', 'shadow', 'canary', 'production', 'archived'
    active_traffic_pct = Column(Float, default=0.0)      # 0.0 to 100.0
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class DatasetVersion(Base):
    """
    Immutable Versioned Dataset Snapshots (SDD Section 22 lines 1506-1509, Section 24.2).
    """
    __tablename__ = "dataset_version"

    id = Column(String(50), primary_key=True)  # e.g., 'ds-2026.01'
    dvc_ref = Column(String(100), nullable=True)
    notes = Column(String(255), nullable=True)
    num_samples = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    samples = relationship("DatasetSample", back_populates="dataset", cascade="all, delete-orphan")

class DatasetSample(Base):
    """
    Individual sample within a dataset version (SDD Section 22 lines 1507-1509).
    Partitioned into train / val / test splits with group-aware splitting.
    """
    __tablename__ = "dataset_sample"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_version_id = Column(String(50), ForeignKey("dataset_version.id"), nullable=False)
    image_id = Column(String(36), ForeignKey("image.id"), nullable=True)
    split = Column(String(20), nullable=False)  # 'train', 'val', 'test'
    labels = Column(JSON, nullable=False)       # {"visual_class_id": "...", "food_id": "...", "variant_id": "...", "grams": ...}
    origin = Column(String(50), default="feedback_review")  # 'seed_benchmark', 'feedback_review', 'weighed_capture'
    perceptual_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    dataset = relationship("DatasetVersion", back_populates="samples")

class FeedbackReview(Base):
    """
    Human Review and Verification on Correction Events (SDD Section 22 lines 1502-1505, Section 23.3).
    Ensures no raw, unreviewed user data enters model training datasets.
    """
    __tablename__ = "feedback_review"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    correction_event_id = Column(String(36), ForeignKey("correction_event.id"), nullable=True)
    correction_batch_id = Column(String(36), nullable=True)
    reviewer_id = Column(String(36), ForeignKey("app_user.id"), nullable=True)
    decision = Column(String(50), nullable=False)  # 'accepted', 'rejected', 'escalated'
    cause = Column(String(50), nullable=True)     # 'visual_misrecognition', 'mapping_error', 'variant_ambiguity', 'taxonomy_gap', 'user_error'
    final_label = Column(JSON, nullable=True)     # Verified canonical food, variant, or visual class
    notes = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
