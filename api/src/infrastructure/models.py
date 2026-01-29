from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime
from datetime import datetime
from infrastructure.db import Base

class EventORM(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
