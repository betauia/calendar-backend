from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import ForeignKey, String, DateTime
from datetime import datetime

# TODO: move all models to separate files

class Base(DeclarativeBase):
    pass

class Event(Base):
    __tablename__ = "Events"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    
class SyncState(Base):
    __tablename__ = "SyncState"
    event_id: Mapped[int] = mapped_column(ForeignKey("Events.id"), primary_key=True)
    provider_name: Mapped[str] = mapped_column(String, primary_key=True)
    external_event_id: Mapped[str] = mapped_column(String)