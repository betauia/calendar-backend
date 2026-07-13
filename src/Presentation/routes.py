from typing import TypeVar

from fastapi import APIRouter, HTTPException

from Application.service_result import ErrorCode, ServiceResult
from Application.sync_service import SyncService
from Application.truth_calendar_orchestrator import TruthCalendarOrchestrator
from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.SyncStatus import SyncStatus
from Domain.ExternalProvider import ExternalProvider
from Domain.ProvidersConfig import ProvidersConfig
from Domain.TruthCalendar import TruthCalendar, TruthCalendarEvent
from Presentation.ViewModels.ErrorResponse import ErrorResponse
from Presentation.ViewModels.SyncStatusResponse import SyncStatusCounts, SyncStatusResponse

T = TypeVar("T")

_ERROR_STATUS_MAP: dict[ErrorCode, int] = {
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONNECTION_ERROR: 502,
    ErrorCode.INVALID_RESPONSE: 502,
    ErrorCode.UNKNOWN: 500,
}

class Routes:
    def __init__(self, sync_service: SyncService, truth_calendar_orchestrator: TruthCalendarOrchestrator, providers: ProvidersConfig) -> None:
        self._sync_service = sync_service
        self._truth_calendar_orchestrator = truth_calendar_orchestrator
        self._providers = providers.external_providers
        self.router = APIRouter()
        self.router.add_api_route("/sync-status", self.get_all_sync_status, methods=["GET"])
        self.router.add_api_route("/sync-status/{provider_name}", self.get_sync_status, methods=["GET"])
        self.router.add_api_route("/providers", self.get_configured_providers, methods=["GET"])
        self.router.add_api_route("/events", self.add_event, methods=["POST"])
        self.router.add_api_route("/events/{event_id}", self.get_event_with_id, methods=["GET"])
        self.router.add_api_route("/events", self.get_events, methods=["GET"])
        self.router.add_api_route("/events/{event_id}", self.delete_event, methods=["DELETE"], status_code=204)
        self.router.add_api_route("/events/{event_id}", self.update_event, methods=["PUT"])

    def _build_sync_status(self, provider: ExternalProvider) -> SyncStatusResponse:
        sync_result = self._sync_service.get_provider_calendar_sync_status(provider)
        return SyncStatusResponse(
            provider=provider.name,
            counts=SyncStatusCounts(
                ahead=sum(1 for e in sync_result.event_statuses if e.sync_status == SyncStatus.AHEAD),
                behind=sum(1 for e in sync_result.event_statuses if e.sync_status == SyncStatus.BEHIND),
                synced=sum(1 for e in sync_result.event_statuses if e.sync_status == SyncStatus.SYNCED),
            )
        )

    def _find_provider(self, provider_name: str) -> ExternalProvider | None:    # Cursed and I hate it. Stems from a lack of ExternalProvider registry.
        return next(
            (p for p in self._providers if p.name.lower() == provider_name.lower()),
            None
        )

    def _unwrap(self, result: ServiceResult[T]) -> T:
        if result.is_successful:
            return result.value  # type: ignore[return-value]
        status = _ERROR_STATUS_MAP.get(result.error_code, 500)
        raise HTTPException(
            status_code=status,
            detail=ErrorResponse(
                error_code=result.error_code.value,
                message=result.error_description or "Unknown error",
            ).model_dump(),
        )
    
    def get_sync_status(self, provider_name: str) -> SyncStatusResponse:
        provider = self._find_provider(provider_name)
        if provider is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND.value,
                    message=f"Provider '{provider_name}' not found",
                ).model_dump(),
            )
        return self._build_sync_status(provider)

    def get_all_sync_status(self) -> list[SyncStatusResponse]:
        return [self._build_sync_status(p) for p in self._providers]

    def get_configured_providers(self) -> list[str]:
        return [p.name for p in self._providers]

    def add_event(self, event_info: CalendarEventInfo) -> TruthCalendarEvent:
        event = self._unwrap(self._truth_calendar_orchestrator.add_event(event_info))
        return event
    
    def get_event_with_id(self, event_id: int) -> TruthCalendarEvent:
        event = self._unwrap(self._truth_calendar_orchestrator.get_event_with_id(event_id))
        return event
    
    def get_events(self) -> TruthCalendar:
        calendar = self._unwrap(self._truth_calendar_orchestrator.get_calendar())
        return calendar
    
    def delete_event(self, event_id: int) -> None:
        self._unwrap(self._truth_calendar_orchestrator.remove_event(event_id))
        
    def update_event(self, event_id: int, event_info: CalendarEventInfo) -> TruthCalendarEvent:     # PUT update, consider adding PATCH update
        event = self._unwrap(self._truth_calendar_orchestrator.update_event(event_id, event_info))
        return event