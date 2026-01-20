# domain/generic_event.py
import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
)
from sqlalchemy.sql import func
from db.base import Base

class GenericEvent(Base):
    __tablename__ = "Events"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # discriminator
    provider = Column(String, nullable=False)

    # generic calendar fields
    name = Column(String, nullable=False)
    description = Column(Text)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    __mapper_args__ = {
        "polymorphic_on": provider,
        "polymorphic_identity": "generic",
    }
