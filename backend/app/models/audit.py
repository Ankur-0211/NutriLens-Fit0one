from datetime import datetime, timezone
from sqlalchemy import Column, String, BigInteger, DateTime, JSON
from backend.app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger().with_variant(BigInteger, "sqlite"), primary_key=True, autoincrement=True)
    actor_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    entity = Column(String(100), nullable=True)
    entity_id = Column(String(100), nullable=True)
    details = Column(JSON, default=dict)
    ip = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
