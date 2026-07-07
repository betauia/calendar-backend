# Application/truth_calendar_orchestrator.py
import logging

from Application.service_result import ServiceResult
from Application.sync_service import SyncService
from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.TruthCalendar import TruthCalendar
from Domain.TruthCalendarEvent import TruthCalendarEvent

from Infrastructure.truth_calendar_service import TruthCalendarService

logger = logging.getLogger(__name__)

class TruthCalendarOrchestrator:

    def __init__(
        self,
        truth_service: TruthCalendarService,
        sync_service: SyncService,
    ) -> None:
        self._truth_service = truth_service
        self._sync_service = sync_service

    def get_calendar(self) -> ServiceResult[TruthCalendar]:
        return self._truth_service.get_calendar()

    def add_event(self, event_info: CalendarEventInfo) -> ServiceResult[TruthCalendarEvent]:
        result = self._truth_service.add_event(event_info)
        if result.is_successful:
            logger.info(f"Event '{event_info.title}' added, triggering sync...")
            # self._sync_service.sync_all()
        return result

    def update_event(self, event: TruthCalendarEvent) -> ServiceResult[TruthCalendarEvent]:
        result = self._truth_service.update_event(event)
        if result.is_successful:
            logger.info(f"Event '{event.title}' updated, triggering sync...")
            self._sync_service.sync_all()
        return result

    def remove_event(self, event_id: int) -> ServiceResult[None]:
        result = self._truth_service.remove_event(event_id)
        if result.is_successful:
            logger.info(f"Event {event_id} removed, triggering sync...")
            self._sync_service.sync_all()
        return result