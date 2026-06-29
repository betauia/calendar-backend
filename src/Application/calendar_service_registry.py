import logging

from src.Application.i_remote_calendar_service import IRemoteCalendarService
from src.Domain.ExternalProvider import ExternalProvider

logger = logging.getLogger(__name__)

class CalendarServiceRegistry:

    def __init__(self) -> None:
        self._services: dict[ExternalProvider, IRemoteCalendarService] = {}

    def register(self, provider: ExternalProvider, service: IRemoteCalendarService) -> None:
        self._services[provider] = service
        logger.info(f"Registered calendar service for provider '{provider.name}'")

    def get(self, provider: ExternalProvider) -> IRemoteCalendarService | None:
        service = self._services.get(provider)
        if service is None:
            logger.warning(f"No service found for provider '{provider.name}'")
        return service

    def get_all(self) -> list[tuple[ExternalProvider, IRemoteCalendarService]]:
        return list(self._services.items())