from infrastructure.db import SessionLocal
from infrastructure.models import EventORM
from domain.event import Event

class EventRepository:
    def list_all(self) -> list[Event]:
        with SessionLocal() as session:
            rows = session.query(EventORM).all()

        return [
            Event.model_validate({
                "id": row.id,
                "title": row.title,
                "start": row.start,
                "end": row.end,
                "updated_at": row.updated_at,
            })
            for row in rows
        ]
