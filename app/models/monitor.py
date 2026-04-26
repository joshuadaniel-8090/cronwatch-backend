import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Supabase Auth user UUID
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)
    interval_seconds = Column(Integer, nullable=False)
    grace_seconds = Column(Integer, default=60)
    token = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    slug = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    is_active = Column(Boolean, default=True)
    last_ping_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="waiting")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # We can link it to profiles if needed, but often user_id is enough for filtering
    profile = relationship("Profile", primaryjoin="Monitor.user_id == Profile.id", foreign_keys=[user_id], backref="monitors")
