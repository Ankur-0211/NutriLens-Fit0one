import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class CorrectionEvent(Base):
    __tablename__ = "correction_event"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    batch_id = Column(String(36), nullable=False)
    analysis_id = Column(String(36), ForeignKey("analysis.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("app_user.id"), nullable=True)
    item_key = Column(String(50), nullable=True)
    event_type = Column(String(50), nullable=False)  # food_changed, variant_changed, quantity_changed, unit_changed, item_added, item_removed, confirmed_unchanged
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
    client_ts = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    review_status = Column(String(50), default="pending")  # pending, auto_rejected, queued, accepted, rejected
