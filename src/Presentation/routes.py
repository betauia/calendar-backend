from fastapi import APIRouter

from Application.sync_service import SyncService
from Domain.ExternalProvider import ExternalProvider
from Domain.ProvidersConfig import ProvidersConfig
from Domain.SyncStatus import SyncStatus
from Presentation.ViewModels.SyncStatusCounts import SyncStatusCounts
from Presentation.ViewModels.SyncStatusResponse import SyncStatusResponse


class Routes:
    def __init__(self, sync_service: SyncService, providers: ProvidersConfig) -> None:
        self._sync_service = sync_service
        self._providers = providers.external_providers
        self.router = APIRouter()
        self.router.add_api_route("/sync-status", self.get_all_sync_status, methods=["GET"])
        self.router.add_api_route("/sync-status/{provider_name}", self.get_sync_status, methods=["GET"])

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

    def get_sync_status(self, provider_name: str) -> SyncStatusResponse:
        provider = self._providers.get(provider_name.lower())
        if provider is None:
            raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")
        return self._build_sync_status(provider)

    def get_all_sync_status(self) -> list[SyncStatusResponse]:
        return [self._build_sync_status(p) for p in self._providers.values()]
