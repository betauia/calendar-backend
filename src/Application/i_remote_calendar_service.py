from typing import Protocol

from Application.service_result import ServiceResult
from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.RemoteCalendarEvent import RemoteCalendarEvent
from Domain.RemoteCalendar import RemoteCalendar


class IRemoteCalendarService(Protocol):
    def get_calendar(self) -> ServiceResult[RemoteCalendar]:
        ...
        
    def add_event(self, event: CalendarEventInfo) -> ServiceResult[str]:
        ...
        
    def update_event(self, updated_event: RemoteCalendarEvent) -> ServiceResult[RemoteCalendarEvent]:
        ...
    
    def remove_event(self, external_id: str) -> ServiceResult[None]:
        ...