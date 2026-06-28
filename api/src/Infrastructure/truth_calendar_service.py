import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from Application.service_result import ServiceResult, ErrorCode
from Domain.TruthCalendar import TruthCalendar
from Domain.TruthCalendarEvent import TruthCalendarEvent
from Infrastructure.calendar_event_orm import Base, CalendarEventORM

logger = logging.getLogger(__name__)

class TruthCalendarService:

    def __init__(self, connection_string: str = "sqlite:///:memory:"):
        engine = create_engine(connection_string)
        Base.metadata.create_all(engine)
        self._session_factory = sessionmaker(bind=engine)

    def get_calendar(self) -> ServiceResult[TruthCalendar]:
        try:
            with self._session_factory() as session:
                logger.info("Getting truth calendar from database...")
                rows = session.scalars(select(CalendarEventORM)).all()
                calendar = TruthCalendar(
                    calendar_events=[row.to_domain() for row in rows]
                )
                return ServiceResult[TruthCalendar](is_successful=True, value=calendar)
        except Exception as e:
            logger.error(f"Failed to get truth calendar: {e}")
            return ServiceResult[TruthCalendar](is_successful=False, error_code=ErrorCode.UNKNOWN, error_description=str(e))

    def add_event(self, event: TruthCalendarEvent) -> ServiceResult[TruthCalendarEvent]:
        with self._session_factory() as session:
            try:
                orm_event = CalendarEventORM.from_domain(event)
                session.add(orm_event)
                session.commit()
                session.refresh(orm_event)
                added_event = orm_event.to_domain()
                logger.info(f"Successfully added event: {event.event_info.title} with id {orm_event.id}")
                return ServiceResult[TruthCalendarEvent](is_successful=True, value=added_event)
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to add event to truth calendar: {e}")
                return ServiceResult[TruthCalendarEvent](is_successful=False, error_code=ErrorCode.UNKNOWN, error_description=str(e))

    def update_event(self, updated_event: TruthCalendarEvent) -> ServiceResult[TruthCalendarEvent]:
        with self._session_factory() as session:
            try:
                row = session.get(CalendarEventORM, updated_event.id)
                if not row:
                    logger.warning(f"Event with id {updated_event.id} not found")
                    return ServiceResult[TruthCalendarEvent](is_successful=False, error_code=ErrorCode.NOT_FOUND, error_description=f"Event with id {updated_event.id} not found")

                row.title = updated_event.event_info.title
                row.description = updated_event.event_info.description
                row.location = updated_event.event_info.location
                row.starts_at = updated_event.event_info.starts_at
                row.ends_at = updated_event.event_info.ends_at
                session.commit()
                session.refresh(row)
                logger.info(f"Updated event: {updated_event.event_info.title}")
                return ServiceResult[TruthCalendarEvent](is_successful=True, value=row.to_domain())
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to update event: {e}")
                return ServiceResult[TruthCalendarEvent](is_successful=False, error_code=ErrorCode.UNKNOWN, error_description=str(e))

    def remove_event(self, event_id: int) -> ServiceResult[None]:
        with self._session_factory() as session:
            try:
                row = session.get(CalendarEventORM, event_id)
                if not row:
                    logger.warning(f"Event with id {event_id} not found")
                    return ServiceResult[None](is_successful=False, error_code=ErrorCode.NOT_FOUND, error_description=f"Event with id {event_id} not found")
                    
                session.delete(row)
                session.commit()
                logger.info(f"Removed event with id: {event_id}")
                return ServiceResult[None](is_successful=True, value=None)
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to remove event: {e}")
                return ServiceResult[None](is_successful=False, error_code=ErrorCode.UNKNOWN, error_description=str(e))