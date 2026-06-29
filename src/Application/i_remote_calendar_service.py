from typing import Protocol

from src.Application.models.DTO.calendar_event_info_dto import CalendarEventInfoDTO
from src.Application.service_result import ServiceResult
from src.Domain.RemoteCalendarEvent import RemoteCalendarEvent
from src.Domain.RemoteCalendar import RemoteCalendar


class IRemoteCalendarService(Protocol):
    def get_calendar(self) -> ServiceResult[RemoteCalendar]:
        ...
        
    def add_event(self, event: CalendarEventInfoDTO) -> ServiceResult[str]:
        ...
        
    def update_event(self, updated_event: CalendarEventInfoDTO) -> ServiceResult[RemoteCalendarEvent]:
        ...
    
    def remove_event(self, external_id: str) -> ServiceResult[None]:
        ...