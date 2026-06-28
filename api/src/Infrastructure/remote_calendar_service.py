import logging
from typing import final

import httpx

from Application.i_remote_calendar_service import IRemoteCalendarService
from Application.models.DTO.calendar_event_info_dto import CalendarEventInfoDTO
from Application.models.DTO.remote_calendar_dto import RemoteCalendarDTO
from Application.service_result import ErrorCode, ServiceResult
from Domain.ExternalProvider import ExternalProvider
from Domain.RemoteCalendar import RemoteCalendar

logger = logging.getLogger(__name__)

@final
class RemoteCalendarService(IRemoteCalendarService):
    def __init__(self, provider: ExternalProvider):
        self._provider = provider
        self._client = httpx.Client()

    def __enter__(self) -> "RemoteCalendarService":
        return self

    def __exit__(self, *args: object) -> None:
        self._client.close()

    def get_calendar(self) -> ServiceResult[RemoteCalendar]:
        try:
            response = self._client.get(f"{self._provider.url}/calendar")
            response.raise_for_status()
            calendar = RemoteCalendarDTO.model_validate(response.json())
            logger.info(f"Successfully fetched calendar ({len(calendar.events)} event(s)) from {self._provider.name}")
            return ServiceResult[RemoteCalendarDTO](is_successful=True, value=calendar)
        except httpx.ConnectError:
            logger.error(f"Could not connect to {self._provider.name} at {self._provider.url}")
            return ServiceResult[RemoteCalendarDTO](is_successful=False, error_code=ErrorCode.CONNECTION_ERROR, error_description=f"Could not connect to {self._provider.url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching calendar from {self._provider.name}: {e}")
            return ServiceResult[RemoteCalendarDTO](is_successful=False, error_code=ErrorCode.UNKNOWN, error_description=str(e))

    def add_event(self, event: CalendarEventInfoDTO) -> ServiceResult[str]:
        try:
            response = self._client.post(
                f"{self._provider.url}/event",
                json=event.model_dump(mode="json")
            )
            response.raise_for_status()
            external_id = response.json()
            logger.info(f"Successfully added event '{event.title}' to {self._provider.name}")
            return ServiceResult[str](is_successful=True, value=external_id)
        except httpx.ConnectError:
            logger.error(f"Could not connect to {self._provider.name} at {self._provider.url}")
            return ServiceResult[str](is_successful=False, error_code=ErrorCode.CONNECTION_ERROR, error_description=f"Could not connect to {self._provider.url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error adding event to {self._provider.name}: {e}")
            return ServiceResult[str](is_successful=False, error_code=ErrorCode.UNKNOWN, error_description=str(e))

    def update_event(self, updated_event: RemoteCalendarEventDTO) -> ServiceResult[RemoteCalendarEventDTO]:
        try:
            response = self._client.put(
                f"{self._provider.url}/event/{updated_event.external_id}",
                json=updated_event.event.model_dump(mode="json")
            )
            response.raise_for_status()
            result = RemoteCalendarEventDTO.model_validate(response.json())
            logger.info(f"Successfully updated event {updated_event.external_id} on {self._provider.name}")
            return ServiceResult[RemoteCalendarEventDTO](is_successful=True, value=result)
        except httpx.ConnectError:
            logger.error(f"Could not connect to {self._provider.name} at {self._provider.url}")
            return ServiceResult[RemoteCalendarEventDTO](is_successful=False, error_code=ErrorCode.CONNECTION_ERROR, error_description=f"Could not connect to {self._provider.url}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Event {updated_event.external_id} not found on {self._provider.name}")
                return ServiceResult[RemoteCalendarEventDTO](is_successful=False, error_code=ErrorCode.NOT_FOUND, error_description=f"Event {updated_event.external_id} not found on {self._provider.name}")
            logger.error(f"HTTP error updating event on {self._provider.name}: {e}")
            return ServiceResult[RemoteCalendarEventDTO](is_successful=False, error_code=ErrorCode.UNKNOWN, error_description=str(e))

    def remove_event(self, external_id: str) -> ServiceResult[None]:
        try:
            response = self._client.delete(f"{self._provider.url}/event/{external_id}")
            response.raise_for_status()
            logger.info(f"Successfully removed event {external_id} from {self._provider.name}")
            return ServiceResult[None](is_successful=True)
        except httpx.ConnectError:
            logger.error(f"Could not connect to {self._provider.name} at {self._provider.url}")
            return ServiceResult[None](is_successful=False, error_code=ErrorCode.CONNECTION_ERROR, error_description=f"Could not connect to {self._provider.url}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Event {external_id} not found on {self._provider.name}")
                return ServiceResult[None](is_successful=False, error_code=ErrorCode.NOT_FOUND, error_description=f"Event {external_id} not found on {self._provider.name}")
            logger.error(f"HTTP error removing event from {self._provider.name}: {e}")
            return ServiceResult[None](is_successful=False, error_code=ErrorCode.UNKNOWN, error_description=str(e))