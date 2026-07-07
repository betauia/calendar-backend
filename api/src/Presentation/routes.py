from typing import Any

from fastapi import APIRouter, Request

from Application.sync_service import SyncService
from Domain.SyncStatus import SyncStatus

router = APIRouter()


@router.get("/syncStatus")
async def get_sync_status(request: Request) -> dict[str, Any]:
    providers = getattr(request.app.state, "providers", [])
    sync_service: SyncService | None = getattr(request.app.state, "sync_service", None)

    if not providers:
        return {"provider": None, "counts": {"ahead": 0, "behind": 0, "synced": 0}}

    if sync_service is None:
        raise RuntimeError("Sync service is not configured")

    provider = providers[0]
    sync_result = sync_service.get_provider_calendar_sync_status(provider)

    ahead = sum(1 for event in sync_result.event_statuses if event.sync_status == SyncStatus.AHEAD)
    behind = sum(1 for event in sync_result.event_statuses if event.sync_status == SyncStatus.BEHIND)
    synced = sum(1 for event in sync_result.event_statuses if event.sync_status == SyncStatus.SYNCED)

    return {
        "provider": provider.name,
        "counts": {
            "ahead": ahead,
            "behind": behind,
            "synced": synced,
        },
    }
