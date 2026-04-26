import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Ping(Base):
    __tablename__ = "pings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_id = Column(UUID(as_uuid=True), ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="ok")

    monitor = relationship("Monitor", backref="pings")
