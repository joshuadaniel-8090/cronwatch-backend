import uuid
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Profile(Base):
    __tablename__ = "profiles"

    # Matches Supabase Auth user UUID
    id = Column(UUID(as_uuid=True), primary_key=True)
    plan = Column(String, default="free")
    telegram_chat_id = Column(String, nullable=True)
    alert_email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
