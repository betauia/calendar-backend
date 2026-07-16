from datetime import datetime, timezone
from unittest.mock import create_autospec

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from Application.models.result.calendar_sync_result import CalendarSyncResult
from Application.models.result.event_sync_result import EventSyncResult
from Application.sync_coordinator import SyncCoordinator
from Application.sync_service import SyncService
from Application.truth_calendar_orchestrator import TruthCalendarOrchestrator
from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.ExternalProvider import ExternalProvider
from Domain.ProvidersConfig import ProvidersConfig
from Domain.RemoteCalendar import RemoteCalendar
from Domain.RemoteCalendarEvent import RemoteCalendarEvent
from Domain.SyncStatus import SyncStatus
from Presentation.routes import Routes


def test_get_sync_status_returns_provider_summary() -> None:
    provider = ExternalProvider(name="Discord", url=HttpUrl("http://discord.com"))
    providers_config = ProvidersConfig(external_providers=[provider])

    sync_service = create_autospec(SyncService, instance=True)
    sync_coordinator = create_autospec(SyncCoordinator, instance=True)
    sync_service.get_provider_calendar_sync_status.return_value = CalendarSyncResult(
        remote_calendar=RemoteCalendar(
            external_provider=provider,
            calendar_events=[
                RemoteCalendarEvent(
                    external_id="ext-1",
                    event_info=CalendarEventInfo(
                        title="Standup",
                        description="Daily",
                        location="Online",
                        starts_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
                        ends_at=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
                    ),
                )
            ],
        ),
        event_statuses=[
            EventSyncResult(
                truth_event=None,
                remote_event=RemoteCalendarEvent(
                    external_id="ext-1",
                    event_info=CalendarEventInfo(
                        title="Standup",
                        description="Daily",
                        location="Online",
                        starts_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
                        ends_at=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
                    ),
                ),
                sync_status=SyncStatus.AHEAD,
            )
        ],
    )

    truth_calendar_orchestrator = create_autospec(TruthCalendarOrchestrator, instance=True)
    routes = Routes(
        sync_service=sync_service,
        sync_coordinator=sync_coordinator,
        truth_calendar_orchestrator=truth_calendar_orchestrator,
        providers=providers_config,
    )
    app = FastAPI()
    app.include_router(routes.router)

    client = TestClient(app)
    response = client.get("/sync-status/discord")

    assert response.status_code == 200
    assert response.json()["provider"] == "Discord"
    assert response.json()["counts"]["ahead"] == 1


def test_get_all_sync_status_returns_all_providers() -> None:
    provider = ExternalProvider(name="Discord", url=HttpUrl("http://discord.com"))
    providers_config = ProvidersConfig(external_providers=[provider])

    sync_service = create_autospec(SyncService, instance=True)
    sync_service.get_provider_calendar_sync_status.return_value = CalendarSyncResult(
        remote_calendar=RemoteCalendar(
            external_provider=provider,
            calendar_events=[],
        ),
        event_statuses=[
            EventSyncResult(
                truth_event=None,
                remote_event=RemoteCalendarEvent(
                    external_id="ext-1",
                    event_info=CalendarEventInfo(
                        title="Standup",
                        description="Daily",
                        location="Online",
                        starts_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
                        ends_at=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
                    ),
                ),
                sync_status=SyncStatus.AHEAD,
            )
        ],
    )

    truth_calendar_orchestrator = create_autospec(TruthCalendarOrchestrator, instance=True)
    sync_coordinator = create_autospec(SyncCoordinator, instance=True)
    routes = Routes(
        sync_service=sync_service,
        sync_coordinator=sync_coordinator,
        truth_calendar_orchestrator=truth_calendar_orchestrator,
        providers=providers_config,
    )
    app = FastAPI()
    app.include_router(routes.router)

    client = TestClient(app)
    response = client.get("/sync-status")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["provider"] == "Discord"
    assert data[0]["counts"]["ahead"] == 1


def test_get_sync_status_unknown_provider_returns_404() -> None:
    providers_config = ProvidersConfig(external_providers=[
        ExternalProvider(name="Discord", url=HttpUrl("http://discord.com"))
    ])

    sync_service = create_autospec(SyncService, instance=True)
    truth_calendar_orchestrator = create_autospec(TruthCalendarOrchestrator, instance=True)
    sync_coordinator = create_autospec(SyncCoordinator, instance=True)
    routes = Routes(
        sync_service=sync_service,
        sync_coordinator=sync_coordinator,
        truth_calendar_orchestrator=truth_calendar_orchestrator,
        providers=providers_config,
    )
    app = FastAPI()
    app.include_router(routes.router)

    client = TestClient(app)
    response = client.get("/sync-status/nonexistent")

    assert response.status_code == 404