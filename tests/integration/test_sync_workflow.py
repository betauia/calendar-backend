import pytest
from datetime import datetime, timezone
from unittest.mock import create_autospec

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from Application.models.result.calendar_sync_result import CalendarSyncResult
from Application.models.result.event_sync_result import EventSyncResult
from Application.sync_service import SyncService
from Application.truth_calendar_orchestrator import TruthCalendarOrchestrator
from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.CalendarEventMetaInfo import CalendarEventMetaInfo
from Domain.ExternalProvider import ExternalProvider
from Domain.ProvidersConfig import ProvidersConfig
from Domain.RemoteCalendar import RemoteCalendar
from Domain.RemoteCalendarEvent import RemoteCalendarEvent
from Domain.SyncStatus import SyncStatus
from Domain.TruthCalendarEvent import TruthCalendarEvent
from Presentation.routes import Routes


@pytest.fixture
def provider() -> ExternalProvider:
    return ExternalProvider(name="Discord", url=HttpUrl("http://discord.com"))


@pytest.fixture
def sync_service() -> SyncService:
    return create_autospec(SyncService, instance=True)


@pytest.fixture
def truth_calendar_orchestrator():
    return create_autospec(object, instance=True)

@pytest.fixture
def client(
    sync_service: SyncService,
    provider: ExternalProvider,
    truth_calendar_orchestrator: TruthCalendarOrchestrator,
) -> TestClient:
    providers_config = ProvidersConfig(external_providers=[provider])
    routes = Routes(
        sync_service=sync_service,
        providers=providers_config,
        truth_calendar_orchestrator=truth_calendar_orchestrator,
        sync_coordinator=create_autospec(object, instance=True),
    )
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


@pytest.fixture
def event_info() -> CalendarEventInfo:
    return CalendarEventInfo(
        title="Standup",
        description="Daily",
        location="Online",
        starts_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
    )


@pytest.fixture
def remote_event(event_info: CalendarEventInfo) -> RemoteCalendarEvent:
    return RemoteCalendarEvent(external_id="ext-1", event_info=event_info)


@pytest.fixture
def truth_event(event_info: CalendarEventInfo) -> TruthCalendarEvent:
    return TruthCalendarEvent(id=1, event_info=event_info, event_meta_info= CalendarEventMetaInfo(created_at=datetime.now(timezone.utc)))


def make_sync_result(
    provider: ExternalProvider,
    event_statuses: list[EventSyncResult],
) -> CalendarSyncResult:
    return CalendarSyncResult(
        remote_calendar=RemoteCalendar(external_provider=provider, calendar_events=[]),
        event_statuses=event_statuses,
    )


# --- /sync-status/{provider_name} ---

# TODO: move to unit test
def test_get_sync_status_unknown_provider_returns_404(client: TestClient) -> None:
    response = client.get("/sync-status/nonexistent")
    assert response.status_code == 404

# TODO: move to unit test
def test_get_sync_status_is_case_insensitive(
    client: TestClient,
    sync_service: SyncService,
    provider: ExternalProvider,
) -> None:
    sync_service.get_provider_calendar_sync_status.return_value = make_sync_result(provider, [])  # type: ignore
    response = client.get("/sync-status/DISCORD")
    assert response.status_code == 200


def test_get_sync_status_ahead_count(
    client: TestClient,
    sync_service: SyncService,
    provider: ExternalProvider,
    remote_event: RemoteCalendarEvent,
) -> None:
    sync_service.get_provider_calendar_sync_status.return_value = make_sync_result(  # type: ignore
        provider,
        [EventSyncResult(truth_event=None, remote_event=remote_event, sync_status=SyncStatus.AHEAD)],
    )

    response = client.get("/sync-status/discord")

    assert response.status_code == 200
    assert response.json()["provider"] == "Discord"
    assert response.json()["counts"]["ahead"] == 1
    assert response.json()["counts"]["behind"] == 0
    assert response.json()["counts"]["synced"] == 0


def test_get_sync_status_behind_count(
    client: TestClient,
    sync_service: SyncService,
    provider: ExternalProvider,
    truth_event: TruthCalendarEvent,
) -> None:
    sync_service.get_provider_calendar_sync_status.return_value = make_sync_result(  # type: ignore
        provider,
        [EventSyncResult(truth_event=truth_event, remote_event=None, sync_status=SyncStatus.BEHIND)],
    )

    response = client.get("/sync-status/discord")

    assert response.status_code == 200
    assert response.json()["counts"]["behind"] == 1
    assert response.json()["counts"]["ahead"] == 0
    assert response.json()["counts"]["synced"] == 0


def test_get_sync_status_synced_count(
    client: TestClient,
    sync_service: SyncService,
    provider: ExternalProvider,
    truth_event: TruthCalendarEvent,
    remote_event: RemoteCalendarEvent,
) -> None:
    sync_service.get_provider_calendar_sync_status.return_value = make_sync_result(  # type: ignore
        provider,
        [EventSyncResult(truth_event=truth_event, remote_event=remote_event, sync_status=SyncStatus.SYNCED)],
    )

    response = client.get("/sync-status/discord")

    assert response.status_code == 200
    assert response.json()["counts"]["synced"] == 1
    assert response.json()["counts"]["ahead"] == 0
    assert response.json()["counts"]["behind"] == 0


def test_get_sync_status_mixed_counts(
    client: TestClient,
    sync_service: SyncService,
    provider: ExternalProvider,
    truth_event: TruthCalendarEvent,
    remote_event: RemoteCalendarEvent,
) -> None:
    sync_service.get_provider_calendar_sync_status.return_value = make_sync_result(  # type: ignore
        provider,
        [
            EventSyncResult(truth_event=None, remote_event=remote_event, sync_status=SyncStatus.AHEAD),
            EventSyncResult(truth_event=truth_event, remote_event=None, sync_status=SyncStatus.BEHIND),
            EventSyncResult(truth_event=truth_event, remote_event=remote_event, sync_status=SyncStatus.SYNCED),
        ],
    )

    response = client.get("/sync-status/discord")

    assert response.status_code == 200
    assert response.json()["counts"]["ahead"] == 1
    assert response.json()["counts"]["behind"] == 1
    assert response.json()["counts"]["synced"] == 1