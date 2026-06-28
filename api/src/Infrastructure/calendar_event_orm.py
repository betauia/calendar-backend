from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.TruthCalendarEvent import TruthCalendarEvent


class Base(DeclarativeBase):
    pass

class CalendarEventORM(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    location: Mapped[str | None] = mapped_column(String)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    
    def to_domain(self) -> TruthCalendarEvent:
        return TruthCalendarEvent(
            id=self.id,
            event_info=CalendarEventInfo(
                title=self.title,
                description=self.description,
                location=self.location,
                starts_at=self.starts_at,
                ends_at=self.ends_at,
                created_at=self.created_at,
                updated_at=self.updated_at)
        )

    @classmethod
    def from_domain(cls, event: TruthCalendarEvent) -> "CalendarEventORM":
        return cls(
            id=event.id,
            title=event.event_info.title,
            description=event.event_info.description,
            location=event.event_info.location,
            starts_at=event.event_info.starts_at,
            ends_at=event.event_info.ends_at,
            created_at=event.event_info.created_at,
            updated_at=event.event_info.updated_at,
        )