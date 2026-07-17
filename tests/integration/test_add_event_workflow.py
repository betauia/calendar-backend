import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from unittest.mock import create_autospec

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from Application.calendar_service_registry import CalendarServiceRegistry
from Application.i_remote_calendar_service import IRemoteCalendarService
from Application.service_result import ServiceResult
from Application.sync_coordinator import SyncCoordinator
from Application.sync_service import SyncService
from Application.truth_calendar_orchestrator import TruthCalendarOrchestrator
from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.ExternalProvider import ExternalProvider
from Domain.ProvidersConfig import ProvidersConfig
from Domain.RemoteCalendar import RemoteCalendar
from Domain.RemoteCalendarEvent import RemoteCalendarEvent
from Domain.SyncStatus import SyncStatus
from Infrastructure.external_event_mapping_store import ExternalEventMappingStore
from Infrastructure.truth_calendar_service import TruthCalendarService
from Presentation.routes import Routes

logger = logging.getLogger(__name__)


# --- Fixtures: real infra, wired the same way main.py does it ---

@pytest.fixture
def provider() -> ExternalProvider:
    return ExternalProvider(name="Discord", url=HttpUrl("http://discord.com"))


@pytest.fixture
def providers_config(provider: ExternalProvider) -> ProvidersConfig:
    return ProvidersConfig(external_providers=[provider])


@pytest.fixture
def mock_remote_service(provider: ExternalProvider) -> IRemoteCalendarService:
    """The only mocked collaborator: no Discord plugin exists yet.

    Stateful rather than a static stub — a real provider would reflect a
    pushed event on the next get_calendar() call, and SyncService's own
    consistency checks (mapping vs. what the remote actually reports) depend
    on that being true.
    """
    service = create_autospec(IRemoteCalendarService, instance=True)
    remote_events: list[RemoteCalendarEvent] = []

    def get_calendar_side_effect() -> ServiceResult[RemoteCalendar]:
        return ServiceResult[RemoteCalendar](
            is_successful=True,
            value=RemoteCalendar(
                external_provider=provider, calendar_events=list(remote_events)
            ),
        )

    def add_event_side_effect(event_info: CalendarEventInfo) -> ServiceResult[str]:
        external_id = f"remote-ext-{len(remote_events) + 1}"
        remote_events.append(
            RemoteCalendarEvent(external_id=external_id, event_info=event_info)
        )
        return ServiceResult[str](is_successful=True, value=external_id)

    service.get_calendar.side_effect = get_calendar_side_effect  # type: ignore
    service.add_event.side_effect = add_event_side_effect  # type: ignore
    return service


@pytest.fixture
def registry(
    provider: ExternalProvider, mock_remote_service: IRemoteCalendarService
) -> CalendarServiceRegistry:
    registry = CalendarServiceRegistry()
    registry.register(provider, mock_remote_service)
    return registry


@pytest.fixture
def truth_service(tmp_path: Path) -> TruthCalendarService:
    # File-based SQLite: avoids the in-memory + thread-pool pitfall that
    # FastAPI's sync-route dispatch to worker threads triggers.
    db_path = tmp_path / "truth_calendar.db"
    return TruthCalendarService(connection_string=f"sqlite:///{db_path}")


@pytest.fixture
def mapping_store() -> ExternalEventMappingStore:
    return ExternalEventMappingStore()


@pytest.fixture
def sync_service(
    truth_service: TruthCalendarService,
    registry: CalendarServiceRegistry,
    mapping_store: ExternalEventMappingStore,
) -> SyncService:
    return SyncService(
        truth_service=truth_service,
        registry=registry,
        mapping_store=mapping_store,
    )


@pytest.fixture
def sync_coordinator(sync_service: SyncService) -> SyncCoordinator:
    return SyncCoordinator(sync_service=sync_service)


@pytest.fixture
def orchestrator(
    truth_service: TruthCalendarService,
    sync_coordinator: SyncCoordinator,
) -> TruthCalendarOrchestrator:
    return TruthCalendarOrchestrator(
        truth_service=truth_service,
        sync_coordinator=sync_coordinator,
    )


@pytest.fixture
def client(
    sync_service: SyncService,
    sync_coordinator: SyncCoordinator,
    orchestrator: TruthCalendarOrchestrator,
    providers_config: ProvidersConfig,
) -> TestClient:
    routes = Routes(
        sync_service=sync_service,
        sync_coordinator=sync_coordinator,
        truth_calendar_orchestrator=orchestrator,
        providers=providers_config,
    )
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


@pytest.fixture
def event_payload() -> dict[str, str]:
    return {
        "title": "Standup",
        "description": "Daily sync",
        "location": "Online",
        "starts_at": datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc).isoformat(),
        "ends_at": datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc).isoformat(),
    }


# --- Tests ---

def test_add_event_persists_to_truth_calendar(
    client: TestClient, event_payload: dict[str, str]
) -> None:
    response = client.post("/events", json=event_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["event_info"]["title"] == "Standup"
    assert body["id"] is not None

    events_response = client.get("/events")
    assert events_response.status_code == 200
    assert len(events_response.json()["calendar_events"]) == 1


def test_add_event_triggers_sync_and_propagates_to_provider(
    client: TestClient,
    event_payload: dict[str, str],
    mock_remote_service: IRemoteCalendarService,
) -> None:
    response = client.post("/events", json=event_payload)
    assert response.status_code == 200

    # SyncCoordinator.request_sync() runs synchronously in-thread, so by the
    # time the response comes back the (mocked) provider has already been hit.
    mock_remote_service.add_event.assert_called_once()  # type: ignore
    called_event_info = cast(
        CalendarEventInfo,
        mock_remote_service.add_event.call_args[0][0],  # type: ignore
    )
    assert called_event_info.title == "Standup"


def test_add_event_updates_mapping_store_to_synced(
    client: TestClient,
    event_payload: dict[str, str],
    mapping_store: ExternalEventMappingStore,
    provider: ExternalProvider,
) -> None:
    response = client.post("/events", json=event_payload)
    truth_event_id = response.json()["id"]

    mapping = mapping_store.get(truth_event_id, provider)

    assert mapping is not None
    assert mapping.external_id == "remote-ext-1"
    assert mapping.status == SyncStatus.SYNCED


def test_add_event_reflected_in_sync_status_endpoint(
    client: TestClient, event_payload: dict[str, str]
) -> None:
    client.post("/events", json=event_payload)

    status_response = client.get("/sync-status/discord")

    assert status_response.status_code == 200
    counts = status_response.json()["counts"]
    assert counts["synced"] == 1
    assert counts["behind"] == 0
    assert counts["ahead"] == 0